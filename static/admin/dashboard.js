(function () {
    async function refreshUsersCount() {
        try {
            const r = await fetch('/admin/api/users'); if (!r.ok) return;
            const data = await r.json();
            const stats = {
                total: data.length,
                superadmin: 0,
                localadmin: 0,
                worker: 0,
                disabled: 0
            };
            data.forEach(u => {
                if (u.role && stats.hasOwnProperty(u.role)) {
                    stats[u.role] += 1;
                }
                if (!u.is_enabled) stats.disabled += 1;
            });

            const map = {
                'users-count': stats.total,
                'count-superadmin': stats.superadmin,
                'count-localadmin': stats.localadmin,
                'count-worker': stats.worker,
                'count-disabled': stats.disabled
            };

            Object.entries(map).forEach(([id, value]) => {
                const el = document.getElementById(id);
                if (el) el.textContent = value;
            });
        } catch (_) {/* noop */ }
    }
    refreshUsersCount();
})();


