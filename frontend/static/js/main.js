document.addEventListener('DOMContentLoaded', () => {
    // ----------------------
    // 1. Theme Configuration
    // ----------------------
    const themeToggleBtn = document.getElementById('theme-toggle');
    const htmlElement = document.documentElement;

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
    // 3. Client-side Search, Filters and Pagination
    // ----------------------
    const searchInput = document.getElementById('search-input');
    const itemCards = document.querySelectorAll('.item-card');
    const paginationContainer = document.getElementById('pagination-container');
    const prevBtn = document.getElementById('prev-page-btn');
    const nextBtn = document.getElementById('next-page-btn');
    const pageNumbersContainer = document.getElementById('page-numbers');
    const perPageSelect = document.getElementById('per-page-select');

    const sortSelect = document.getElementById('sort-select');
    const inventoryGrid = document.getElementById('inventory-grid');

    if (itemCards.length > 0 && paginationContainer) {
        let currentPage = 1;
        let itemsPerPage = parseInt(perPageSelect.value) || 25;
        let filteredCards = Array.from(itemCards);

        function updatePagination() {
            const totalItems = filteredCards.length;
            const totalPages = Math.ceil(totalItems / itemsPerPage) || 1;

            if (totalItems === 0) {
                paginationContainer.style.display = 'none';
                itemCards.forEach(card => card.style.display = 'none');
                return;
            }

            paginationContainer.style.display = 'flex';

            // Clamp currentPage
            if (currentPage > totalPages) currentPage = totalPages;
            if (currentPage < 1) currentPage = 1;

            // Hide all cards first
            itemCards.forEach(card => card.style.display = 'none');

            // Show cards for the current page
            const startIndex = (currentPage - 1) * itemsPerPage;
            const endIndex = startIndex + itemsPerPage;
            filteredCards.slice(startIndex, endIndex).forEach(card => {
                card.style.display = 'flex';
            });

            // Update buttons state
            prevBtn.disabled = currentPage === 1;
            nextBtn.disabled = currentPage === totalPages;

            // Render page numbers
            pageNumbersContainer.innerHTML = '';
            
            // Basic sliding window pagination for page numbers
            const maxPageButtons = 5;
            let startPage = Math.max(1, currentPage - Math.floor(maxPageButtons / 2));
            let endPage = Math.min(totalPages, startPage + maxPageButtons - 1);
            if (endPage - startPage + 1 < maxPageButtons) {
                startPage = Math.max(1, endPage - maxPageButtons + 1);
            }

            for (let i = startPage; i <= endPage; i++) {
                const btn = document.createElement('button');
                btn.className = `page-btn${i === currentPage ? ' active' : ''}`;
                btn.textContent = i;
                btn.addEventListener('click', () => {
                    currentPage = i;
                    updatePagination();
                    const grid = document.getElementById('inventory-grid');
                    if (grid) grid.scrollIntoView({ behavior: 'smooth' });
                });
                pageNumbersContainer.appendChild(btn);
            }
        }

        function sortCards() {
            if (!sortSelect || !inventoryGrid) {
                updatePagination();
                return;
            }
            const sortVal = sortSelect.value;
            const [field, direction] = sortVal.split('-');
            const cardsArray = Array.from(itemCards);

            cardsArray.sort((a, b) => {
                let valA, valB;
                if (field === 'price' || field === 'cost') {
                    valA = parseFloat(a.getAttribute(`data-${field}`)) || 0;
                    valB = parseFloat(b.getAttribute(`data-${field}`)) || 0;
                } else {
                    valA = (a.getAttribute(`data-${field}`) || '').toLowerCase();
                    valB = (b.getAttribute(`data-${field}`) || '').toLowerCase();
                }

                if (valA < valB) return direction === 'asc' ? -1 : 1;
                if (valA > valB) return direction === 'asc' ? 1 : -1;
                return 0;
            });

            // Re-append sorted cards in DOM
            cardsArray.forEach(card => inventoryGrid.appendChild(card));
            
            // Re-apply search/filter
            const query = searchInput ? searchInput.value.toLowerCase().trim() : '';
            filteredCards = cardsArray.filter(card => {
                const name = (card.getAttribute('data-name') || '').toLowerCase();
                const type = (card.getAttribute('data-type') || '').toLowerCase();
                const customId = (card.getAttribute('data-custom-id') || '').toLowerCase();
                return name.includes(query) || type.includes(query) || customId.includes(query);
            });

            currentPage = 1;
            updatePagination();
        }

        // Search integration
        if (searchInput) {
            searchInput.addEventListener('input', function() {
                sortCards(); // Sort on input changes to keep order correct
            });
        }

        // Sort Select Change
        if (sortSelect) {
            sortSelect.addEventListener('change', function() {
                sortCards();
            });
        }

        // Per page change
        if (perPageSelect) {
            perPageSelect.addEventListener('change', function() {
                itemsPerPage = parseInt(this.value) || 25;
                currentPage = 1;
                updatePagination();
            });
        }

        // Prev / Next button actions
        if (prevBtn) {
            prevBtn.addEventListener('click', () => {
                if (currentPage > 1) {
                    currentPage--;
                    updatePagination();
                    const grid = document.getElementById('inventory-grid');
                    if (grid) grid.scrollIntoView({ behavior: 'smooth' });
                }
            });
        }

        if (nextBtn) {
            nextBtn.addEventListener('click', () => {
                const totalPages = Math.ceil(filteredCards.length / itemsPerPage) || 1;
                if (currentPage < totalPages) {
                    currentPage++;
                    updatePagination();
                    const grid = document.getElementById('inventory-grid');
                    if (grid) grid.scrollIntoView({ behavior: 'smooth' });
                }
            });
        }

        // Initial run - Sort first
        sortCards();
    } else if (searchInput) {
        // Fallback search behavior if on a page without pagination
        searchInput.addEventListener('input', function() {
            const query = this.value.toLowerCase().trim();
            itemCards.forEach(card => {
                const name = card.querySelector('.item-name') ? card.querySelector('.item-name').textContent.toLowerCase() : '';
                const type = card.querySelector('.item-type-badge') ? card.querySelector('.item-type-badge').textContent.toLowerCase() : '';
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
