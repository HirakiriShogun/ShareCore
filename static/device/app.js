(function () {
    const uid = document.querySelector('[data-device-uid]').dataset.deviceUid;
    const priceKopecks = parseInt(document.querySelector('[data-device-price]').dataset.devicePrice);

    const ppmRubEl = document.getElementById('ppm-rub');
    const busyBanner = document.getElementById('busy-banner');
    const remainMM = document.getElementById('remain-mm');
    const remainSS = document.getElementById('remain-ss');
    const totalEl = document.getElementById('total');
    const msgBox = document.getElementById('msg');
    const payBtn = document.getElementById('pay');
    const chipsContainer = document.getElementById('chips');
    const controls = document.getElementById('controls');
    const agreementCheckbox1 = document.getElementById('agreement-checkbox-1');
    const agreementCheckbox2 = document.getElementById('agreement-checkbox-2');

    ppmRubEl.textContent = (priceKopecks / 100).toFixed(2);

    let minutes = 10;
    let remaining = 0;
    let serverBusy = false;
    let online = true;
    let allowedMinutes = null;
    let userSelectedMinutes = null; // Сохраняем выбор пользователя

    function setActiveChip(m, isUserAction = false) {
        minutes = m;
        if (isUserAction) {
            userSelectedMinutes = m; // Запоминаем выбор пользователя
        }
        [...chipsContainer.children].forEach(b =>
            b.classList.toggle('active', +b.dataset.min === m)
        );
        totalEl.textContent = ((priceKopecks * minutes) / 100).toFixed(2);
    }

    chipsContainer.addEventListener('click', (e) => {
        const btn = e.target.closest('button');
        if (!btn) return;
        setActiveChip(+btn.dataset.min, true); // Указываем, что это действие пользователя
    });

    setInterval(() => {
        if (remaining > 0) {
            remaining--;
            renderRemain();
        }
    }, 1000);

    function renderRemain() {
        const m = Math.floor(remaining / 60);
        const s = remaining % 60;
        remainMM.textContent = String(m).padStart(2, '0');
        remainSS.textContent = String(s).padStart(2, '0');

        const busy = remaining > 0;
        busyBanner.classList.toggle('hidden', !busy);
        controls.classList.toggle('hidden', busy || !online);
        updatePayButtonState();
    }

    function updatePayButtonState() {
        const busy = remaining > 0;
        const agreement1Accepted = agreementCheckbox1 ? agreementCheckbox1.checked : true;
        const agreement2Accepted = agreementCheckbox2 ? agreementCheckbox2.checked : true;
        payBtn.disabled = busy || !online || !agreement1Accepted || !agreement2Accepted;
    }

    // Обновляем состояние кнопки при изменении чекбоксов
    if (agreementCheckbox1) {
        agreementCheckbox1.addEventListener('change', updatePayButtonState);
    }
    if (agreementCheckbox2) {
        agreementCheckbox2.addEventListener('change', updatePayButtonState);
    }

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
            serverBusy = !!d.busy;

            if (!online) {
                controls.classList.add('hidden');
                payBtn.disabled = true;
                return;
            } else {
                controls.classList.remove('hidden');
            }

            const allowed = Array.isArray(d.allowed_minutes) && d.allowed_minutes.length
                ? d.allowed_minutes
                : [5, 10, 15, 30, 60];

            // Обновляем чипсы только если изменился список доступного времени
            const allowedStr = allowed.sort((a, b) => a - b).join(',');
            if (allowedStr !== allowedMinutes) {
                allowedMinutes = allowedStr;
                chipsContainer.innerHTML = allowed
                    .map(m => `<button class="time-chip" data-min="${m}">${m} мин</button>`)
                    .join('');

                // Восстанавливаем выбор пользователя или ставим дефолт
                if (userSelectedMinutes && allowed.includes(userSelectedMinutes)) {
                    setActiveChip(userSelectedMinutes);
                } else {
                    const defaultMin = allowed.includes(10) ? 10 : allowed[0];
                    setActiveChip(defaultMin);
                }
            }

            remaining = d.remaining_seconds || 0;
            renderRemain();
        } catch (_e) {
            // Network error - keep current state
        }
    }

    setActiveChip(10);
    poll();
    setInterval(poll, 1500);

  payBtn.addEventListener('click', async () => {
    msgBox.className = 'message-box hidden';
    msgBox.textContent = '';
    
    // Проверяем принятие обоих соглашений
    if (agreementCheckbox1 && !agreementCheckbox1.checked) {
      msgBox.className = 'message-box error';
      msgBox.textContent = 'Необходимо принять пользовательское соглашение и согласие на обработку персональных данных.';
      return;
    }
    
    if (agreementCheckbox2 && !agreementCheckbox2.checked) {
      msgBox.className = 'message-box error';
      msgBox.textContent = 'Необходимо принять публичную оферту и согласие на оплату банковскими картами.';
      return;
    }
    
    payBtn.disabled = true;
    
    try {
      // Пробуем создать платеж через эквайринг
      const r = await fetch('/api/payment/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ device_uid: uid, minutes })
      });

      const data = await r.json();
      
      // Если эквайринг отключён или недоступен, используем прямой запуск
      if (r.status === 400 && data.error === 'acquiring_disabled') {
        const fallbackR = await fetch('/api/rent', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ device_uid: uid, minutes })
        });
        
        const fallbackData = await fallbackR.json();
        
        if (!fallbackR.ok) {
          handlePaymentError(fallbackData, fallbackR.ok);
        } else {
          handlePaymentSuccess(fallbackData);
        }
        return;
      }

      // Обрабатываем ошибки
      if (!r.ok) {
        handlePaymentError(data, r.ok);
      } else if (data.payment_url) {
        // Перенаправляем на страницу оплаты Альфа-Банка
        msgBox.className = 'message-box success';
        msgBox.textContent = 'Перенаправление на оплату...';
        setTimeout(() => {
          window.location.href = data.payment_url;
        }, 500);
      } else {
        msgBox.className = 'message-box error';
        msgBox.textContent = 'Ошибка создания платежа.';
      }
    } catch (e) {
      msgBox.className = 'message-box error';
      msgBox.textContent = 'Сеть недоступна. Попробуйте позже.';
    } finally {
      updatePayButtonState();
    }
  });

  // Вспомогательные функции для обработки платежа
  function handlePaymentError(data, isOk) {
    if (data && data.error === 'busy') {
      remaining = data.remaining_seconds || 0;
      renderRemain();
      msgBox.className = 'message-box error';
      msgBox.textContent = 'Устройство занято. Подождите завершения.';
    } else if (data && data.error === 'device_unavailable') {
      controls.classList.add('hidden');
      msgBox.className = 'message-box error';
      msgBox.textContent = 'Устройство недоступно.';
    } else {
      msgBox.className = 'message-box error';
      msgBox.textContent = 'Ошибка оплаты. Попробуйте ещё раз.';
    }
  }

  function handlePaymentSuccess(data) {
    const untilIso = data.until;
    const until = new Date(untilIso).getTime();
    const now = Date.now();
    remaining = Math.max(0, Math.floor((until - now) / 1000));
    renderRemain();
    msgBox.className = 'message-box success';
    msgBox.textContent = `Оплата прошла! Таймер запущен на ${minutes} мин.`;
  }

    // Parallax effect for desktop
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

    // Mobile floating animation
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

    // Visual viewport height fix for mobile
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
