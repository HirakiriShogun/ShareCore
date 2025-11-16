// ShareCore Home Page - Device Showcase

(function() {
    'use strict';

    // DOM Elements
    const devicesGrid = document.getElementById('devices-grid');
    const devicesLoading = document.getElementById('devices-loading');
    const devicesEmpty = document.getElementById('devices-empty');

    // API Helper
    async function fetchJSON(url) {
        try {
            const response = await fetch(url, {
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('Fetch error:', error);
            throw error;
        }
    }

    // Format price in rubles
    function formatPrice(kopeks) {
        const rubles = kopeks / 100;
        return rubles.toLocaleString('ru-RU', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    }

    // Format remaining time
    function formatTime(seconds) {
        if (!seconds || seconds <= 0) return '—';
        const minutes = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
    }

    // Create device card HTML
    function createDeviceCard(device) {
        const isOnline = device.online;
        const isBusy = device.busy && device.remaining_seconds > 0;
        
        let statusClass;
        let statusText;
        
        if (!isOnline) {
            statusClass = 'status-offline';
            statusText = 'Офлайн';
        } else if (isBusy) {
            statusClass = 'status-busy';
            statusText = `Активно ещё ${formatTime(device.remaining_seconds)}`;
        } else {
            statusClass = 'status-online';
            statusText = 'Свободно';
        }

        const pricePerMin = formatPrice(device.price_per_minute);
        const deviceUrl = `/device/${device.id}`;

        return `
            <div class="device-card" data-device-id="${device.id}">
                <div class="device-header">
                    <div>
                        <h3 class="device-name">${escapeHtml(device.name)}</h3>
                        <div class="device-status ${statusClass}">
                            <span class="status-dot"></span>
                            ${statusText}
                        </div>
                    </div>
                </div>
                
                <div class="device-price">
                    Стоимость: <strong>${pricePerMin} ₽</strong>/мин
                </div>
                
                <div class="device-info">
                    ${device.allowed_minutes && device.allowed_minutes.length > 0 ? `
                        <div style="color: var(--muted); font-size: 0.9rem;">
                            Доступные пакеты: ${device.allowed_minutes.join(', ')} мин
                        </div>
                    ` : ''}
                </div>
                
                <div class="device-link">
                    ${isOnline ? `
                        <a href="${deviceUrl}" class="btn ${isBusy ? 'btn-secondary' : 'btn-primary'}" ${isBusy ? 'style="pointer-events: none; opacity: 0.6;"' : ''}>
                            ${isBusy ? 'Устройство занято' : 'Перейти к устройству'}
                        </a>
                    ` : `
                        <button class="btn btn-secondary" disabled style="opacity: 0.5;">
                            Недоступно
                        </button>
                    `}
                </div>
            </div>
        `;
    }

    // Escape HTML to prevent XSS
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Load devices from API
    async function loadDevices() {
        try {
            // Show loading state
            devicesLoading.style.display = 'block';
            devicesGrid.innerHTML = '';
            devicesEmpty.style.display = 'none';

            // Fetch devices
            const devices = await fetchJSON('/api/devices');

            // Hide loading
            devicesLoading.style.display = 'none';

            // Check if we have devices
            if (!devices || devices.length === 0) {
                devicesEmpty.style.display = 'block';
                return;
            }

            // Render devices
            const cardsHTML = devices.map(device => createDeviceCard(device)).join('');
            devicesGrid.innerHTML = cardsHTML;

            // Add animation
            const cards = devicesGrid.querySelectorAll('.device-card');
            cards.forEach((card, index) => {
                card.style.opacity = '0';
                card.style.transform = 'translateY(20px)';
                setTimeout(() => {
                    card.style.transition = 'all 0.5s ease';
                    card.style.opacity = '1';
                    card.style.transform = 'translateY(0)';
                }, index * 100);
            });

        } catch (error) {
            console.error('Failed to load devices:', error);
            devicesLoading.style.display = 'none';
            devicesEmpty.style.display = 'block';
            devicesEmpty.querySelector('p').textContent = 
                'Не удалось загрузить устройства. Пожалуйста, обновите страницу.';
        }
    }

    // Check if we need to create /api/devices endpoint
    async function checkAPIEndpoint() {
        try {
            const response = await fetch('/api/devices');
            return response.ok;
        } catch {
            return false;
        }
    }

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

    // Initialize on page load
    window.addEventListener('DOMContentLoaded', () => {
        loadDevices();
        
        // Refresh devices every 10 seconds
        setInterval(() => {
            loadDevices();
        }, 10000);
    });

    // Expose reload function for debugging
    window.reloadDevices = loadDevices;

})();


