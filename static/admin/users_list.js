(function () {
    const $ = (s) => document.querySelector(s);
    const api = (u, opt = {}) => fetch(u, { headers: { 'Content-Type': 'application/json' }, ...opt });
    let allUsers = [];

    function cardHtml(user) {
        const roleClass = user.role === 'superadmin' ? 'role-sa' : user.role === 'localadmin' ? 'role-la' : 'role-worker';
        const statusText = user.is_enabled ? 'Активен' : 'Выключен';
        const toggleLabel = user.is_enabled ? 'Отключить' : 'Включить';
        const canImpersonate = user.role === 'localadmin' && user.is_enabled;

        return `
      <div class="admin-card user-card" data-id="${user.id}">
        <div class="user-card__header">
          <div>
            <div class="title">${user.email}</div>
            <div class="user-meta">ID ${user.id}</div>
          </div>
          <div class="pills">
            <span class="pill ${roleClass}">${user.role}</span>
            <span class="pill ${user.is_enabled ? 'on' : 'off'}">${statusText}</span>
          </div>
        </div>
        <div class="card-actions">
          ${canImpersonate ? `<button class="btn small btn-blue" data-act="imp">Войти как</button>` : ``}
          ${user.role === 'localadmin' ? `<button class="btn small btn-warn" data-act="toggle">${toggleLabel}</button>` : ``}
          ${user.role !== 'superadmin' ? `<button class="btn small btn-red" data-act="del" style="margin-left:auto">Удалить</button>` : ``}
        </div>
      </div>`;
    }

    function bindActions(row) {
        row.addEventListener('click', async (e) => {
            const btn = e.target.closest('button'); if (!btn) return;
            const id = row.dataset.id; const act = btn.dataset.act;
            if (act === 'del') {
                const r = await api(`/admin/api/users/${id}`, { method: 'DELETE' });
                if (r.ok) refresh();
            }
            if (act === 'toggle') {
                const r = await api(`/admin/api/users/${id}/toggle`, { method: 'POST' });
                if (r.ok) refresh();
            }
            if (act === 'imp') {
                const r = await api(`/admin/impersonate/${id}`, { method: 'POST' });
                if (r.ok) {
                    const d = await r.json();
                    location.href = d.redirect || '/local/';
                }
            }
        });
    }

    function render(list) {
        const box = $('#users-list'); if (!box) return;
        box.innerHTML = '';
        list.forEach(u => {
            const w = document.createElement('div');
            w.innerHTML = cardHtml(u);
            const row = w.firstElementChild;
            bindActions(row);
            box.appendChild(row);
        });
    }

    async function refresh() {
        const r = await api('/admin/api/users');
        allUsers = await r.json();
        applyFilter();
    }

    function applyFilter() {
        const role = document.querySelector('#role-chips .is-active')?.getAttribute('data-role') || 'all';
        const q = ($('#search')?.value || '').toLowerCase();
        const byRole = role === 'all' ? allUsers : allUsers.filter(u => u.role === role);
        const list = q ? byRole.filter(u => (u.email || '').toLowerCase().includes(q)) : byRole;
        render(list);
    }

    document.getElementById('search')?.addEventListener('input', applyFilter);
    document.querySelectorAll('#role-chips .chip').forEach(ch => ch.addEventListener('click', () => {
        document.querySelectorAll('#role-chips .chip').forEach(x => x.classList.remove('is-active'));
        ch.classList.add('is-active');
        applyFilter();
    }));

    refresh();
})();
