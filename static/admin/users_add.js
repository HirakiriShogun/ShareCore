(function () {
    const $ = (s) => document.querySelector(s);
    const api = (u, opt = {}) => fetch(u, { headers: { 'Content-Type': 'application/json' }, ...opt });
    const btn = document.getElementById('u-add');
    if (!btn) return;

    const email = document.getElementById('u-email');
    const pass = document.getElementById('u-pass');
    const eye = document.getElementById('u-eye');

    if (eye && pass) {
        eye.addEventListener('click', () => {
            const isPwd = pass.getAttribute('type') === 'password';
            pass.setAttribute('type', isPwd ? 'text' : 'password');
        });
    }

    btn.addEventListener('click', async () => {
        const payload = { email: email.value.trim(), password: pass.value.trim(), role: $('#u-role').value };
        let hasErr = false;
        [email, pass].forEach(el => el.classList.remove('is-invalid'));
        if (!payload.email) { email.classList.add('is-invalid'); hasErr = true; }
        if (!payload.password) { pass.classList.add('is-invalid'); hasErr = true; }
        if (hasErr) return;
        const r = await api('/admin/api/users', { method: 'POST', body: JSON.stringify(payload) });
        const msg = document.getElementById('msg');
        if (r.ok) { msg.textContent = 'Создано'; email.value = ''; pass.value = ''; }
        else { const d = await r.json().catch(() => ({ error: 'error' })); msg.textContent = d.error || 'Ошибка'; }
    });
})();


