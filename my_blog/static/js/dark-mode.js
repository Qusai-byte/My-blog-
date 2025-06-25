// Dark mode toggle
const darkModeToggle = document.getElementById('dark-mode-toggle');
const darkModeStyle = document.getElementById('dark-mode-style');

// Check for saved theme preference
const currentTheme = localStorage.getItem('theme');
if (currentTheme === 'dark') {
    enableDarkMode();
}

// Toggle dark mode
darkModeToggle?.addEventListener('click', () => {
    if (document.body.classList.contains('dark-mode')) {
        disableDarkMode();
    } else {
        enableDarkMode();
    }
});

function enableDarkMode() {
    document.body.classList.add('dark-mode');
    darkModeStyle.disabled = false;
    darkModeToggle.innerHTML = '<i class="fas fa-sun"></i>';
    localStorage.setItem('theme', 'dark');
}

function disableDarkMode() {
    document.body.classList.remove('dark-mode');
    darkModeStyle.disabled = true;
    darkModeToggle.innerHTML = '<i class="fas fa-moon"></i>';
    localStorage.setItem('theme', 'light');
}