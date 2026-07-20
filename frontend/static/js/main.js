document.addEventListener('DOMContentLoaded', () => {
    // ----------------------
    // 1. Theme Configuration
    // ----------------------
    const themeToggleBtn = document.getElementById('theme-toggle');
    const htmlElement = document.documentElement;

    // Load initial theme
    const savedTheme = localStorage.getItem('theme') || 'light';
    htmlElement.setAttribute('data-theme', savedTheme);

    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', () => {
            const currentTheme = htmlElement.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            htmlElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
        });
    }

    // ----------------------
    // 2. Photo Upload Preview
    // ----------------------
    const photoInput = document.getElementById('photo-input');
    const previewContainer = document.getElementById('preview-container');

    if (photoInput && previewContainer) {
        photoInput.addEventListener('change', function() {
            const file = this.files[0];
            if (file) {
                const reader = new FileReader();
                reader.addEventListener('load', function() {
                    previewContainer.innerHTML = `<img src="${this.result}" alt="Preview">`;
                });
                reader.readAsDataURL(file);
            } else {
                previewContainer.innerHTML = '<span>No photo selected</span>';
            }
        });
    }

    // ----------------------
    // 3. Client-side Search and Filters
    // ----------------------
    const searchInput = document.getElementById('search-input');
    const itemCards = document.querySelectorAll('.item-card');

    if (searchInput) {
        searchInput.addEventListener('input', function() {
            const query = this.value.toLowerCase().trim();

            itemCards.forEach(card => {
                const name = card.querySelector('.item-name').textContent.toLowerCase();
                const type = card.querySelector('.item-type-badge').textContent.toLowerCase();
                const customId = (card.getAttribute('data-custom-id') || '').toLowerCase();

                if (name.includes(query) || type.includes(query) || customId.includes(query)) {
                    card.style.display = 'flex';
                } else {
                    card.style.display = 'none';
                }
            });
        });
    }

    // ----------------------
    // 4. Mobile Menu Toggle
    // ----------------------
    const menuToggle = document.getElementById('menu-toggle');
    const navLinks = document.getElementById('nav-links');

    if (menuToggle && navLinks) {
        menuToggle.addEventListener('click', (e) => {
            e.stopPropagation();
            navLinks.classList.toggle('active');
        });

        document.addEventListener('click', (e) => {
            if (navLinks.classList.contains('active') && !navLinks.contains(e.target) && e.target !== menuToggle) {
                navLinks.classList.remove('active');
            }
        });
    }

    // ----------------------
    // 5. Dismiss Flash Messages
    // ----------------------
    const flashCloseButtons = document.querySelectorAll('.flash-close-btn');
    flashCloseButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const flashMessage = btn.closest('.flash-message');
            if (flashMessage) {
                flashMessage.classList.add('fade-out');
                flashMessage.addEventListener('transitionend', () => {
                    flashMessage.remove();
                });
            }
        });
    });
});
