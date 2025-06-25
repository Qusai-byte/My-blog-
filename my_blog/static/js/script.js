// Toggle mobile menu
document.querySelector('.menu-toggle')?.addEventListener('click', function() {
    document.querySelector('nav').classList.toggle('active');
});

// Close flash messages
document.querySelectorAll('.close-flash').forEach(button => {
    button.addEventListener('click', function() {
        this.closest('.flash').remove();
    });
});

// Auto-hide flash messages after 5 seconds
setTimeout(() => {
    document.querySelectorAll('.flash').forEach(flash => {
        flash.remove();
    });
}, 5000);