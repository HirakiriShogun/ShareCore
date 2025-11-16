(function () {
    async function refreshUsersCount() {
        try {
            const r = await fetch('/admin/api/users'); if (!r.ok) return;
            const data = await r.json();
            const badge = document.getElementById('users-count');
            if (badge) badge.textContent = data.length;
        } catch (_) {/* noop */ }
    }
    refreshUsersCount();
})();


