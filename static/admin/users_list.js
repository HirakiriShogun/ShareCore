(function () {
    const $ = (s) => document.querySelector(s);
    const api = (u, opt = {}) => fetch(u, { headers: { 'Content-Type': 'application/json' }, ...opt });
    let allUsers = [];

    function pill(text, type) {
        const styles = {
            on: 'background: rgba(34,197,94,.14); color:#86efac; border:1px solid rgba(34,197,94,.35);',
            off: 'background: rgba(239,68,68,.14); color:#fecaca; border:1px solid rgba(239,68,68,.35);',
            role: 'background: rgba(59,130,246,.14); color:#bfdbfe; border:1px solid rgba(59,130,246,.35);'
        };
        const style = type === 'on' ? styles.on : type === 'off' ? styles.off : styles.role;
        return `<span class="pill" style="${style} padding:6px 10px; border-radius:999px; font-size:12px;">${text}</span>`;
    }

    function cardHtml(u) {
        const statePill = `<span class="pill ${u.is_enabled ? 'on' : 'off'}" style="padding:6px 10px; border-radius:999px; font-size:12px;">${u.is_enabled ? 'Включён' : 'Выключен'}</span>`;
        const roleClass = u.role === 'superadmin' ? 'role-sa' : u.role === 'localadmin' ? 'role-la' : 'role-worker';
        const rolePill = `<span class="pill ${roleClass}" style="padding:6px 10px; border-radius:999px; font-size:12px;">${u.role}</span>`;
        const toggleLabel = u.is_enabled ? 'Выключить' : 'Включить';
        const canImpersonate = (u.role === 'localadmin' && u.is_enabled);
        return `
      <div class="admin-card user-card" data-id="${u.id}">
        <div class="title" style="text-align:center; background: linear-gradient(90deg, var(--accent-soft), var(--accent)); -webkit-background-clip:text; background-clip:text; color:transparent; text-shadow:0 0 24px rgba(var(--accent-rgb), .2);">${u.email}</div>
        <div class="pills" style="justify-content:center;">
          ${rolePill}
          ${statePill}
        </div>
        <div class="card-actions">
          ${canImpersonate ? `<button class="btn small btn-blue" data-act="imp">Зайти как</button>` : ``}
          ${u.role === 'localadmin' ? `<button class="btn small btn-warn" data-act="toggle">${toggleLabel}</button>` : ``}
          ${u.role !== 'superadmin' ? `<button class="btn small btn-red" data-act="del" style="margin-left:auto">Удалить</button>` : ``}
        </div>
      </div>`;
    }

    function bindActions(row) {
        row.addEventListener('click', async (e) => {
            const btn = e.target.closest('button'); if (!btn) return;
            const id = row.dataset.id; const act = btn.dataset.act;
            if (act === 'del') {
                const r = await api(`/admin/api/users/${id}`, { method: 'DELETE' }); if (r.ok) refresh();
            }
            if (act === 'toggle') {
                const r = await api(`/admin/api/users/${id}/toggle`, { method: 'POST' }); if (r.ok) refresh();
            }
            if (act === 'imp') {
                const r = await api(`/admin/impersonate/${id}`, { method: 'POST' });
                if (r.ok) { const d = await r.json(); location.href = d.redirect || '/local/'; }
            }
        });
    }

    function render(list) {
        const box = $('#users-list'); if (!box) return; box.innerHTML = '';
        list.forEach(u => {
            const w = document.createElement('div'); w.innerHTML = cardHtml(u);
            const row = w.firstElementChild; bindActions(row); box.appendChild(row);
        });
    }

    async function refresh() {
        const r = await api('/admin/api/users'); allUsers = await r.json();
        applyFilter();
    }

    function applyFilter() {
        const role = document.querySelector('.chips .is-active')?.getAttribute('data-role') || 'all';
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


