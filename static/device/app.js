(function () {
    const uid = document.querySelector('[data-device-uid]').dataset.deviceUid;
    let priceKopecks = parseInt(document.querySelector('[data-device-price]').dataset.devicePrice, 10);

    const ppmRubEl = document.getElementById('ppm-rub');
    const busyBanner = document.getElementById('busy-banner');
    const remainMM = document.getElementById('remain-mm');
    const remainSS = document.getElementById('remain-ss');
    const msgBox = document.getElementById('msg');
    const payBtn = document.getElementById('pay');
    const payText = payBtn ? payBtn.querySelector('span') : null;
    const controls = document.getElementById('controls');
    const agreementCheckbox1 = document.getElementById('agreement-checkbox-1');
    const agreementCheckbox2 = document.getElementById('agreement-checkbox-2');
    const emailInput = document.getElementById('client-email');
    const timeChips = document.getElementById('time-chips');
    const totalAmount = document.getElementById('total-amount');

    const formatRub = (kopecks) => (kopecks / 100).toLocaleString('ru-RU', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });

    const defaultMinutes = [5, 10, 15, 30, 60];
    let remaining = 0;
    let online = true;
    let isSubmitting = false;
    let selectedMinutes = 0;
    let minutesKey = '';

    function setPrice(value) {
        if (ppmRubEl) {
            ppmRubEl.textContent = formatRub(value);
        }
    }

    function normalizeMinutes(list) {
        const src = Array.isArray(list) && list.length ? list : defaultMinutes;
        const unique = [];
        src.forEach((value) => {
            const parsed = parseInt(value, 10);
            if (Number.isFinite(parsed) && parsed > 0 && !unique.includes(parsed)) {
                unique.push(parsed);
            }
        });
        return unique;
    }

    function updateTotal() {
        if (!totalAmount) {
            return;
        }
        if (!selectedMinutes) {
            totalAmount.textContent = '-';
            return;
        }
        const sum = priceKopecks * selectedMinutes;
        totalAmount.textContent = `${formatRub(sum)} ₽`;
    }

    function updateChipSelection() {
        if (!timeChips) {
            return;
        }
        timeChips.querySelectorAll('.time-chip').forEach((btn) => {
            const minutes = parseInt(btn.dataset.minutes || '0', 10);
            btn.classList.toggle('active', minutes === selectedMinutes);
        });
    }

    function selectMinutes(value) {
        selectedMinutes = value;
        updateChipSelection();
        updateTotal();
        updateButtonState();
    }

    function setMinutesOptions(list) {
        const normalized = normalizeMinutes(list);
        const key = normalized.join(',');
        if (key === minutesKey && (!timeChips || timeChips.children.length)) {
            return;
        }
        minutesKey = key;
        if (timeChips) {
            timeChips.innerHTML = '';
            normalized.forEach((minutes) => {
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'time-chip';
                btn.dataset.minutes = String(minutes);
                btn.textContent = `${minutes} мин`;
                btn.addEventListener('click', () => selectMinutes(minutes));
                timeChips.appendChild(btn);
            });
        }
        if (!normalized.includes(selectedMinutes)) {
            selectedMinutes = normalized.includes(10) ? 10 : (normalized[0] || 0);
        }
        updateChipSelection();
        updateTotal();
        updateButtonState();
    }

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

        const hasMinutes = selectedMinutes > 0;
        payBtn.disabled = busy || !online || !agreement1Accepted || !agreement2Accepted || !emailOk || !hasMinutes || isSubmitting;
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

    setPrice(priceKopecks);
    setMinutesOptions(defaultMinutes);
    updateTotal();

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

            if (typeof d.price_per_minute === 'number') {
                priceKopecks = d.price_per_minute;
                setPrice(priceKopecks);
                updateTotal();
            }
            setMinutesOptions(d.allowed_minutes);

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

        if (!selectedMinutes) {
            msgBox.className = 'message-box error';
            msgBox.textContent = 'Выберите длительность аренды.';
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

        isSubmitting = true;
        const oldText = payText ? payText.textContent : payBtn.textContent;
        if (payText) {
            payText.textContent = 'Перенаправляем...';
        } else {
            payBtn.textContent = 'Перенаправляем...';
        }
        updateButtonState();

        try {
            const consentResponse = await fetch('/api/consent', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ device_uid: uid, email: emailValue, agreed: true })
            });
            const consentData = await consentResponse.json().catch(() => ({}));

            if (!consentResponse.ok) {
                if (consentData && consentData.error === 'consent_required') {
                    msgBox.className = 'message-box error';
                    msgBox.textContent = 'Согласие обязательно.';
                } else {
                    msgBox.className = 'message-box error';
                    msgBox.textContent = 'Не удалось сохранить согласие.';
                }
                return;
            }

            const paymentResponse = await fetch('/api/payment/public/create', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ device_uid: uid, minutes: selectedMinutes })
            });
            const paymentData = await paymentResponse.json().catch(() => ({}));

            if (!paymentResponse.ok) {
                if (paymentData.error === 'acquiring_disabled') {
                    msgBox.className = 'message-box error';
                    msgBox.textContent = paymentData.message || 'Онлайн-оплата временно недоступна.';
                } else if (paymentData.error === 'minutes_not_allowed') {
                    msgBox.className = 'message-box error';
                    msgBox.textContent = 'Выбранная длительность недоступна.';
                } else if (paymentData.error === 'busy') {
                    msgBox.className = 'message-box error';
                    msgBox.textContent = 'Устройство занято, попробуйте позже.';
                } else if (paymentData.error === 'device_unavailable') {
                    msgBox.className = 'message-box error';
                    msgBox.textContent = 'Устройство недоступно.';
                } else if (paymentData.error === 'payment_creation_failed') {
                    msgBox.className = 'message-box error';
                    msgBox.textContent = paymentData.message || 'Не удалось создать оплату.';
                } else {
                    msgBox.className = 'message-box error';
                    msgBox.textContent = 'Ошибка создания оплаты.';
                }
                return;
            }

            if (paymentData && paymentData.payment_url) {
                window.location.href = paymentData.payment_url;
                return;
            }

            msgBox.className = 'message-box error';
            msgBox.textContent = 'Не удалось получить ссылку на оплату.';
        } catch (e) {
            msgBox.className = 'message-box error';
            msgBox.textContent = 'Сеть недоступна. Попробуйте позже.';
        } finally {
            isSubmitting = false;
            if (payText) {
                payText.textContent = oldText;
            } else {
                payBtn.textContent = oldText;
            }
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
