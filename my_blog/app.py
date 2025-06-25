import os
from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, Email, EqualTo
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
from PIL import Image

app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 8 * 1024 * 1024  # 8MB max upload size
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# نماذج قاعدة البيانات
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_admin = db.Column(db.Boolean, default=False)
    posts = db.relationship('Post', backref='author', lazy=True)
    comments = db.relationship('Comment', backref='user', lazy=True)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    image = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    comments = db.relationship('Comment', backref='post', lazy=True)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    posts = db.relationship('Post', backref='category', lazy=True)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)

# نماذج النماذج
class RegistrationForm(FlaskForm):
    username = StringField('اسم المستخدم', validators=[DataRequired(), Length(min=3, max=20)])
    email = StringField('البريد الإلكتروني', validators=[DataRequired(), Email()])
    password = PasswordField('كلمة المرور', validators=[DataRequired()])
    confirm_password = PasswordField('تأكيد كلمة المرور', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('تسجيل حساب')

class LoginForm(FlaskForm):
    email = StringField('البريد الإلكتروني', validators=[DataRequired(), Email()])
    password = PasswordField('كلمة المرور', validators=[DataRequired()])
    submit = SubmitField('تسجيل الدخول')

class PostForm(FlaskForm):
    title = StringField('عنوان المنشور', validators=[DataRequired(), Length(min=5, max=200)])
    content = TextAreaField('المحتوى', validators=[DataRequired()])
    image = FileField('صورة المنشور', validators=[FileAllowed(['jpg', 'jpeg', 'png', 'gif'])])
    category = StringField('التصنيف (اختياري)')
    submit = SubmitField('نشر المنشور')

class CommentForm(FlaskForm):
    content = TextAreaField('التعليق', validators=[DataRequired(), Length(min=2, max=500)])
    submit = SubmitField('إرسال التعليق')

# وظائف المساعدة
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def save_image(image_file):
    if image_file and allowed_file(image_file.filename):
        filename = secure_filename(image_file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # إنشاء مجلد التحميل إذا لم يكن موجودًا
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # حفظ الصورة الأصلية
        image_file.save(filepath)
        
        # إنشاء نسخة مصغرة
        img = Image.open(filepath)
        img.thumbnail((600, 400))
        thumbnail_path = os.path.join(app.config['UPLOAD_FOLDER'], 'thumb_' + filename)
        img.save(thumbnail_path)
        
        return filename
    return None

# إعدادات تسجيل الدخول
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# معالج السياق لجلب التصنيفات
@app.context_processor
def inject_categories():
    categories = Category.query.limit(5).all()
    return dict(categories=categories)

# المسارات
@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 6
    posts = Post.query.order_by(Post.created_at.desc()).paginate(page=page, per_page=per_page)
    return render_template('index.html', posts=posts)

@app.route('/post/<int:id>', methods=['GET', 'POST'])
def show_post(id):
    post = Post.query.get_or_404(id)
    form = CommentForm()
    
    if form.validate_on_submit():
        if not current_user.is_authenticated:
            flash('يجب تسجيل الدخول لإضافة تعليق', 'warning')
            return redirect(url_for('login'))
        
        new_comment = Comment(
            content=form.content.data,
            user_id=current_user.id,
            post_id=post.id
        )
        db.session.add(new_comment)
        db.session.commit()
        flash('تم إضافة تعليقك بنجاح!', 'success')
        return redirect(url_for('show_post', id=post.id))
    
    return render_template('post.html', post=post, form=form)

@app.route('/create', methods=['GET', 'POST'])
@login_required
def create_post():
    form = PostForm()
    
    if form.validate_on_submit():
        image_filename = save_image(form.image.data) if form.image.data else None
        
        # معالجة التصنيف
        category_name = form.category.data.strip()
        category = None
        if category_name:
            category = Category.query.filter_by(name=category_name).first()
            if not category:
                category = Category(name=category_name)
                db.session.add(category)
                db.session.commit()
        
        new_post = Post(
            title=form.title.data,
            content=form.content.data,
            image=image_filename,
            user_id=current_user.id,
            category_id=category.id if category else None
        )
        
        db.session.add(new_post)
        db.session.commit()
        flash('تم إنشاء المنشور بنجاح!', 'success')
        return redirect(url_for('index'))
    
    return render_template('create.html', form=form)

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_post(id):
    post = Post.query.get_or_404(id)
    
    # التحقق من أن المستخدم هو صاحب المنشور أو مدير
    if post.author != current_user and not current_user.is_admin:
        abort(403)
    
    form = PostForm(obj=post)
    
    if form.validate_on_submit():
        # تحديث الصورة إذا تم رفع صورة جديدة
        if form.image.data:
            # حذف الصورة القديمة إذا كانت موجودة
            if post.image:
                try:
                    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], post.image))
                    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], 'thumb_' + post.image))
                except OSError:
                    pass
            post.image = save_image(form.image.data)
        
        # معالجة التصنيف
        category_name = form.category.data.strip()
        if category_name:
            category = Category.query.filter_by(name=category_name).first()
            if not category:
                category = Category(name=category_name)
                db.session.add(category)
                db.session.commit()
            post.category_id = category.id
        else:
            post.category_id = None
        
        post.title = form.title.data
        post.content = form.content.data
        db.session.commit()
        flash('تم تحديث المنشور بنجاح!', 'success')
        return redirect(url_for('show_post', id=post.id))
    
    # تعبئة حقل التصنيف
    form.category.data = post.category.name if post.category else ''
    return render_template('edit.html', form=form, post=post)

@app.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete_post(id):
    post = Post.query.get_or_404(id)
    
    # التحقق من أن المستخدم هو صاحب المنشور أو مدير
    if post.author != current_user and not current_user.is_admin:
        abort(403)
    
    # حذف الصورة المرفقة إذا كانت موجودة
    if post.image:
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], post.image))
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], 'thumb_' + post.image))
        except OSError:
            pass
    
    db.session.delete(post)
    db.session.commit()
    flash('تم حذف المنشور بنجاح!', 'success')
    return redirect(url_for('index'))

@app.route('/delete-comment/<int:id>', methods=['POST'])
@login_required
def delete_comment(id):
    comment = Comment.query.get_or_404(id)
    
    # التحقق من أن المستخدم هو صاحب التعليق أو مدير
    if comment.user != current_user and not current_user.is_admin:
        abort(403)
    
    post_id = comment.post.id
    db.session.delete(comment)
    db.session.commit()
    flash('تم حذف التعليق بنجاح!', 'success')
    return redirect(url_for('show_post', id=post_id))

@app.route('/category/<string:name>')
def category_posts(name):
    category = Category.query.filter_by(name=name).first_or_404()
    page = request.args.get('page', 1, type=int)
    per_page = 6
    posts = Post.query.filter_by(category_id=category.id).order_by(Post.created_at.desc()).paginate(page=page, per_page=per_page)
    return render_template('index.html', posts=posts, category_name=name)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data)
        user = User(
            username=form.username.data,
            email=form.email.data,
            password=hashed_password
        )
        db.session.add(user)
        db.session.commit()
        flash('تم إنشاء حسابك بنجاح! يمكنك الآن تسجيل الدخول', 'success')
        return redirect(url_for('login'))
    
    return render_template('auth/register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            flash('تم تسجيل الدخول بنجاح!', 'success')
            return redirect(next_page or url_for('index'))
        else:
            flash('فشل تسجيل الدخول. يرجى التحقق من البريد الإلكتروني وكلمة المرور', 'danger')
    
    return render_template('auth/login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('تم تسجيل الخروج بنجاح!', 'success')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    user_posts = Post.query.filter_by(user_id=current_user.id).order_by(Post.created_at.desc()).limit(5).all()
    return render_template('dashboard.html', user=current_user, posts=user_posts)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(403)
def forbidden(e):
    return render_template('403.html'), 403

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # إنشاء حساب مدير إذا لم يكن موجود
        if not User.query.filter_by(is_admin=True).first():
            admin = User(
                username='admin',
                email='admin@example.com',
                password=generate_password_hash('admin123'),
                is_admin=True
            )
            db.session.add(admin)
            db.session.commit()
        
        # إنشاء تصنيفات تجريبية
        if not Category.query.first():
            categories = ['تطوير الويب', 'التعلم الآلي', 'أمن المعلومات', 'تطوير تطبيقات الجوال']
            for cat in categories:
                db.session.add(Category(name=cat))
            db.session.commit()
        
        # إنشاء منشورات تجريبية
        if not Post.query.first():
            user = User.query.first()
            categories = Category.query.all()
            
            sample_posts = [
                {
                    'title': 'مرحبًا بكم في المدونة',
                    'content': 'هذه هي المدونة الأولى باستخدام Flask و SQLite مع دعم متكامل للصور والتصنيفات.',
                    'category': categories[0] if categories else None
                },
                {
                    'title': 'دليل Flask للمبتدئين',
                    'content': 'دليل شامل لتعلم Flask من الصفر إلى الاحتراف مع أمثلة عملية.',
                    'category': categories[0] if categories else None
                },
                {
                    'title': 'نصائح لتطوير الويب',
                    'content': 'أفضل الممارسات لتطوير تطبيقات الويب الحديثة.',
                    'category': categories[1] if categories else None
                }
            ]
            
            for post_data in sample_posts:
                post = Post(
                    title=post_data['title'],
                    content=post_data['content'],
                    user_id=user.id,
                    category_id=post_data['category'].id if post_data['category'] else None
                )
                db.session.add(post)
            db.session.commit()
    
    app.run(debug=True)