// ShareCore Home Page - UI helpers

(function() {
    'use strict';
    // Mobile menu toggle
    const mobileMenuToggle = document.querySelector('.mobile-menu-toggle');
    const headerNav = document.querySelector('.header-nav');
    const mobileMenuOverlay = document.querySelector('.mobile-menu-overlay');

    function closeMobileMenu() {
        if (mobileMenuToggle) mobileMenuToggle.classList.remove('active');
        if (headerNav) headerNav.classList.remove('active');
        if (mobileMenuOverlay) mobileMenuOverlay.classList.remove('active');
        document.body.style.overflow = '';
    }

    function openMobileMenu() {
        if (mobileMenuToggle) mobileMenuToggle.classList.add('active');
        if (headerNav) headerNav.classList.add('active');
        if (mobileMenuOverlay) mobileMenuOverlay.classList.add('active');
        document.body.style.overflow = 'hidden';
    }

    if (mobileMenuToggle && headerNav) {
        mobileMenuToggle.addEventListener('click', (e) => {
            e.stopPropagation();
            if (headerNav.classList.contains('active')) {
                closeMobileMenu();
            } else {
                openMobileMenu();
            }
        });

        // Close menu when clicking on a link
        headerNav.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', () => {
                closeMobileMenu();
            });
        });

        // Close menu when clicking overlay
        if (mobileMenuOverlay) {
            mobileMenuOverlay.addEventListener('click', () => {
                closeMobileMenu();
            });
        }

        // Close menu on escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && headerNav.classList.contains('active')) {
                closeMobileMenu();
            }
        });
    }

    // Contact modal
    const contactModal = document.getElementById('contact-modal');
    const modalCloseBtn = document.getElementById('modal-close');
    const modalTriggers = document.querySelectorAll('.open-modal');

    if (contactModal) {
        const openContactModal = () => {
            contactModal.classList.add('is-open');
            contactModal.setAttribute('aria-hidden', 'false');
            document.body.style.overflow = 'hidden';
        };

        const closeContactModal = () => {
            contactModal.classList.remove('is-open');
            contactModal.setAttribute('aria-hidden', 'true');
            document.body.style.overflow = '';
        };

        modalTriggers.forEach(trigger => {
            trigger.addEventListener('click', (event) => {
                event.preventDefault();
                openContactModal();
            });
        });

        if (modalCloseBtn) {
            modalCloseBtn.addEventListener('click', closeContactModal);
        }

        contactModal.addEventListener('click', (event) => {
            if (event.target === contactModal) {
                closeContactModal();
            }
        });

        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape' && contactModal.classList.contains('is-open')) {
                closeContactModal();
            }
        });
    }

    // Smooth scroll for anchor links (only for anchor links, not document links)
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        // Skip document links
        if (anchor.classList.contains('document-link')) {
            return;
        }
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                const headerOffset = 80;
                const elementPosition = target.getBoundingClientRect().top;
                const offsetPosition = elementPosition + window.pageYOffset - headerOffset;

                window.scrollTo({
                    top: offsetPosition,
                    behavior: 'smooth'
                });
            }
        });
    });

    // Ensure document links work on mobile
    document.querySelectorAll('.document-link').forEach(link => {
        // Remove any event listeners that might prevent default
        link.addEventListener('touchstart', function(e) {
            // Allow touch events
            e.stopPropagation();
        }, { passive: true });
        
        link.addEventListener('touchend', function(e) {
            // Ensure click happens
            e.stopPropagation();
        }, { passive: true });
        
        link.addEventListener('click', function(e) {
            // Ensure navigation happens
            const href = this.getAttribute('href');
            if (href && !href.startsWith('#')) {
                // Allow normal navigation for non-anchor links
                return true;
            }
        });
    });

    // Header scroll effect
    let lastScroll = 0;
    const header = document.querySelector('.site-header');

    window.addEventListener('scroll', () => {
        const currentScroll = window.pageYOffset;
        
        if (currentScroll > 100) {
            header.style.padding = '16px 6%';
            header.style.background = 'rgba(11, 17, 25, 0.95)';
        } else {
            header.style.padding = '20px 6%';
            header.style.background = 'rgba(11, 17, 25, 0.85)';
        }
        
        lastScroll = currentScroll;
    });

})();


