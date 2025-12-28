(function () {
    const uid = document.querySelector('[data-device-uid]').dataset.deviceUid;
    const priceKopecks = parseInt(document.querySelector('[data-device-price]').dataset.devicePrice, 10);

    const ppmRubEl = document.getElementById('ppm-rub');
    const busyBanner = document.getElementById('busy-banner');
    const remainMM = document.getElementById('remain-mm');
    const remainSS = document.getElementById('remain-ss');
    const msgBox = document.getElementById('msg');
    const payBtn = document.getElementById('pay');
    const controls = document.getElementById('controls');
    const agreementCheckbox1 = document.getElementById('agreement-checkbox-1');
    const agreementCheckbox2 = document.getElementById('agreement-checkbox-2');
    const emailInput = document.getElementById('client-email');

    if (ppmRubEl) {
        ppmRubEl.textContent = (priceKopecks / 100).toFixed(2);
    }

    let remaining = 0;
    let online = true;
    let consentSent = false;

    function renderRemain() {
        const m = Math.floor(remaining / 60);
        const s = remaining % 60;
        remainMM.textContent = String(m).padStart(2, '0');
        remainSS.textContent = String(s).padStart(2, '0');

        const busy = remaining > 0;
        busyBanner.classList.toggle('hidden', !busy);
        controls.classList.toggle('hidden', busy || !online);
        updateButtonState();
    }

    function updateButtonState() {
        const busy = remaining > 0;
        const agreement1Accepted = agreementCheckbox1 ? agreementCheckbox1.checked : true;
        const agreement2Accepted = agreementCheckbox2 ? agreementCheckbox2.checked : true;
        const emailValue = (emailInput && emailInput.value || '').trim();
        const emailOk = emailValue.length > 0 && emailValue.includes('@');

        payBtn.disabled = busy || !online || !agreement1Accepted || !agreement2Accepted || !emailOk || consentSent;
    }

    if (agreementCheckbox1) {
        agreementCheckbox1.addEventListener('change', updateButtonState);
    }
    if (agreementCheckbox2) {
        agreementCheckbox2.addEventListener('change', updateButtonState);
    }
    if (emailInput) {
        emailInput.addEventListener('input', updateButtonState);
    }

    setInterval(() => {
        if (remaining > 0) {
            remaining--;
            renderRemain();
        }
    }, 1000);

    async function poll() {
        try {
            const r = await fetch(`/api/device/${uid}`);
            if (!r.ok) {
                online = false;
                controls.classList.add('hidden');
                payBtn.disabled = true;
                return;
            }
            const d = await r.json();
            online = !!d.online;

            if (!online) {
                controls.classList.add('hidden');
                payBtn.disabled = true;
                return;
            } else {
                controls.classList.remove('hidden');
            }

            remaining = d.remaining_seconds || 0;
            renderRemain();
        } catch (_e) {
            // Network error - keep current state
        }
    }

    updateButtonState();
    poll();
    setInterval(poll, 1500);

    payBtn.addEventListener('click', async () => {
        msgBox.className = 'message-box hidden';
        msgBox.textContent = '';

        const emailValue = (emailInput && emailInput.value || '').trim();
        if (!emailValue || !emailValue.includes('@')) {
            msgBox.className = 'message-box error';
            msgBox.textContent = 'Введите корректный email.';
            return;
        }

        if (agreementCheckbox1 && !agreementCheckbox1.checked) {
            msgBox.className = 'message-box error';
            msgBox.textContent = 'Необходимо принять условия публичной оферты.';
            return;
        }

        if (agreementCheckbox2 && !agreementCheckbox2.checked) {
            msgBox.className = 'message-box error';
            msgBox.textContent = 'Необходимо согласиться с политиками обработки данных.';
            return;
        }

        payBtn.disabled = true;

        try {
            const r = await fetch('/api/consent', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ device_uid: uid, email: emailValue, agreed: true })
            });
            const data = await r.json().catch(() => ({}));

            if (!r.ok) {
                if (data && data.error === 'consent_required') {
                    msgBox.className = 'message-box error';
                    msgBox.textContent = 'Согласие обязательно.';
                } else {
                    msgBox.className = 'message-box error';
                    msgBox.textContent = 'Не удалось сохранить согласие.';
                }
                return;
            }

            consentSent = true;
            msgBox.className = 'message-box success';
            msgBox.textContent = 'Согласие зафиксировано. Ожидайте включения устройства.';
        } catch (e) {
            msgBox.className = 'message-box error';
            msgBox.textContent = 'Сеть недоступна. Попробуйте позже.';
        } finally {
            updateButtonState();
        }
    });

    const prefersReduced = window.matchMedia &&
        window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const supportsFinePointer = window.matchMedia('(pointer:fine)').matches;
    const card = document.querySelector('.device-card');
    const blobA = document.querySelector('.bg-blob-a');
    const blobB = document.querySelector('.bg-blob-b');

    if (!prefersReduced && card && supportsFinePointer) {
        let rafId = null;
        const onMove = (e) => {
            const rect = card.getBoundingClientRect();
            const cx = rect.left + rect.width / 2;
            const cy = rect.top + rect.height / 2;
            const dx = (e.clientX - cx) / rect.width;
            const dy = (e.clientY - cy) / rect.height;

            if (rafId) cancelAnimationFrame(rafId);

            rafId = requestAnimationFrame(() => {
                const tiltX = (-dy * 1.2).toFixed(2);
                const tiltY = (dx * 1.8).toFixed(2);
                card.style.transform = `perspective(1100px) rotateX(${tiltX}deg) rotateY(${tiltY}deg)`;

                if (blobA) {
                    blobA.style.transform = `translate3d(${(dx * 10).toFixed(1)}px, ${(dy * 6).toFixed(1)}px, 0)`;
                }
                if (blobB) {
                    blobB.style.transform = `translate3d(${(-dx * 8).toFixed(1)}px, ${(-dy * 5).toFixed(1)}px, 0)`;
                }
            });
        };

        const reset = () => {
            card.style.transform = '';
            if (blobA) blobA.style.transform = '';
            if (blobB) blobB.style.transform = '';
        };

        window.addEventListener('mousemove', onMove, { passive: true });
        window.addEventListener('mouseleave', reset, { passive: true });
    }

    if (!supportsFinePointer && !prefersReduced) {
        const cardEl = document.querySelector('.device-card');
        let t = 0;

        const animate = () => {
            t += 0.012;
            const wobble = Math.sin(t) * 0.4;
            if (cardEl) {
                cardEl.style.transform = `translateY(${wobble}px)`;
            }
            requestAnimationFrame(animate);
        };

        requestAnimationFrame(animate);
    }

    const page = document.querySelector('.device-page');
    const vvh = () => {
        const vh = window.visualViewport
            ? window.visualViewport.height
            : window.innerHeight;
        if (page) page.style.minHeight = vh + 'px';
    };

    vvh();
    window.addEventListener('resize', vvh);
    if (window.visualViewport) {
        window.visualViewport.addEventListener('resize', vvh);
    }
})();
