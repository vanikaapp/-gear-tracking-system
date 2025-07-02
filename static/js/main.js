document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips if any
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Auto-focus first input in forms
    const firstInput = document.querySelector('form input:not([type="hidden"]), form select, form textarea');
    if (firstInput) {
        firstInput.focus();
    }

    // Confirm dialogs for delete actions
    document.querySelectorAll('[data-confirm]').forEach(element => {
        element.addEventListener('click', function(e) {
            const message = this.getAttribute('data-confirm');
            if (!confirm(message)) {
                e.preventDefault();
            }
        });
    });

    // Mobile-friendly table scrolling indicator
    const tables = document.querySelectorAll('.table-responsive');
    tables.forEach(table => {
        const scrollContainer = table;
        const tableElement = table.querySelector('table');
        
        if (tableElement && scrollContainer.scrollWidth > scrollContainer.clientWidth) {
            // Add visual indicator for horizontal scroll
            table.classList.add('has-scroll');
            
            // Add scroll event for better UX
            scrollContainer.addEventListener('scroll', function() {
                const isAtStart = this.scrollLeft === 0;
                const isAtEnd = this.scrollLeft >= (this.scrollWidth - this.clientWidth);
                
                this.classList.toggle('scroll-start', isAtStart);
                this.classList.toggle('scroll-end', isAtEnd);
            });
        }
    });

    // Enhanced search functionality
    const searchInputs = document.querySelectorAll('input[name="search"]');
    searchInputs.forEach(input => {
        let timeout;
        input.addEventListener('input', function() {
            clearTimeout(timeout);
            const form = this.closest('form');
            
            // Auto-submit search after 500ms of no typing
            timeout = setTimeout(() => {
                if (this.value.length >= 2 || this.value.length === 0) {
                    form.submit();
                }
            }, 500);
        });
    });

    // Form validation only for actual search forms - don't interfere with add/edit forms
    const searchForms = document.querySelectorAll('form[method="GET"] input[name="search"]');
    searchForms.forEach(searchInput => {
        const form = searchInput.closest('form');
        if (form) {
            form.addEventListener('submit', function(e) {
                if (!form.checkValidity()) {
                    e.preventDefault();
                    e.stopPropagation();
                    searchInput.focus();
                }
                form.classList.add('was-validated');
            });
        }
    });

    // Remove all submit button interference - let forms work naturally
    // Only add loading states to very specific buttons that we know need it
    const returnButtons = document.querySelectorAll('button[type="submit"][onclick*="return"]');
    returnButtons.forEach(button => {
        button.addEventListener('click', function() {
            const form = this.closest('form');
            if (form && form.checkValidity()) {
                this.disabled = true;
                const originalText = this.innerHTML;
                this.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status"></span>Processing...';
                
                // Re-enable after 3 seconds as fallback
                setTimeout(() => {
                    this.disabled = false;
                    this.innerHTML = originalText;
                }, 3000);
            }
        });
    });

    // Touch-friendly dropdown improvements for mobile
    if ('ontouchstart' in window) {
        const dropdowns = document.querySelectorAll('.dropdown-toggle');
        dropdowns.forEach(dropdown => {
            dropdown.addEventListener('touchstart', function() {
                // Add touch feedback
                this.classList.add('touching');
                setTimeout(() => {
                    this.classList.remove('touching');
                }, 150);
            });
        });
    }

    // Quick navigation shortcuts
    document.addEventListener('keydown', function(e) {
        // Only handle shortcuts when not in input fields
        if (e.target.tagName.toLowerCase() === 'input' || 
            e.target.tagName.toLowerCase() === 'textarea' || 
            e.target.tagName.toLowerCase() === 'select') {
            return;
        }

        // Alt+H for home
        if (e.altKey && e.key === 'h') {
            window.location.href = '/';
        }
        // Alt+T for trailers
        else if (e.altKey && e.key === 't') {
            window.location.href = '/trailers';
        }
        // Alt+G for gear
        else if (e.altKey && e.key === 'g') {
            window.location.href = '/gear-snapshots';
        }
        // Alt+R for reports
        else if (e.altKey && e.key === 'r') {
            window.location.href = '/reports';
        }
    });
});

// Utility function for AJAX requests (if needed in future)
function makeRequest(url, method = 'GET', data = null) {
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json',
        }
    };

    if (data) {
        options.body = JSON.stringify(data);
    }

    return fetch(url, options)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .catch(error => {
            console.error('Request failed:', error);
            throw error;
        });
}

// Add custom CSS for enhanced mobile experience
const style = document.createElement('style');
style.textContent = `
    .table-responsive.has-scroll {
        position: relative;
    }
    
    .table-responsive.has-scroll::after {
        content: '→';
        position: absolute;
        right: 0;
        top: 50%;
        transform: translateY(-50%);
        background: var(--bs-dark);
        color: var(--bs-light);
        padding: 0.25rem;
        border-radius: 0.25rem;
        font-size: 0.875rem;
        opacity: 0.7;
        pointer-events: none;
    }
    
    .table-responsive.scroll-end::after {
        display: none;
    }
    
    .btn.touching {
        transform: scale(0.95);
        transition: transform 0.1s ease;
    }
    
    @media (max-width: 768px) {
        .table-responsive {
            border: 1px solid var(--bs-border-color);
            border-radius: 0.375rem;
        }
        
        .card {
            margin-bottom: 1rem;
        }
        
        .btn-group .btn {
            padding: 0.375rem 0.5rem;
        }
        
        .btn-group .btn .d-none.d-md-inline {
            display: none !important;
        }
    }
`;
document.head.appendChild(style);
