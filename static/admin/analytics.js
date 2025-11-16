(function () {
    // Теперь значение уже в рублях, не нужно делить на 100
    const rub = v => v.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' ₽';
    let sortKey = 'name';
    let sortDir = 'asc';
    let byDevice = [];

    function renderMetrics(d) {
        const eo = document.getElementById('k-orders'); if (eo) eo.textContent = d.total_orders;
        const ea = document.getElementById('k-amount'); if (ea) ea.textContent = rub(d.total_amount || 0);
        const ed = document.getElementById('k-devs'); if (ed) ed.textContent = (d.by_device || []).length;
    }

    function renderTable() {
        const box = document.getElementById('bydev'); if (!box) return; box.innerHTML = '';
        const data = [...byDevice].sort((a, b) => {
            const A = sortKey === 'name' ? (a.name || '') : (sortKey === 'amount' ? (a.amount || 0) : (a.orders || 0));
            const B = sortKey === 'name' ? (b.name || '') : (sortKey === 'amount' ? (b.amount || 0) : (b.orders || 0));
            if (A === B) return 0; return (A > B ? 1 : -1) * (sortDir === 'asc' ? 1 : -1);
        });
        data.forEach(x => {
            const row = document.createElement('div'); row.className = 't-row';
            row.innerHTML = `
        <div class="t-cell"><b>${x.name}</b></div>
        <div class="t-cell amt">${rub(x.amount || 0)}</div>
        <div class="t-cell"><span class="orders-text">${x.orders} активаций</span></div>
      `;
            box.appendChild(row);
        });
    }

    async function load() {
        const range = (document.getElementById('range')?.value) || 'month';
        const r = await fetch(`/admin/api/analytics/summary?range=${encodeURIComponent(range)}`);
        if (!r.ok) return;
        const d = await r.json();
        byDevice = d.by_device || [];
        renderMetrics(d);
        renderTable();
    }

    document.querySelectorAll('.t-cell.th').forEach(btn => {
        btn.addEventListener('click', () => {
            const key = btn.getAttribute('data-sort');
            if (sortKey === key) { sortDir = (sortDir === 'asc' ? 'desc' : 'asc'); } else { sortKey = key; sortDir = 'asc'; }
            document.querySelectorAll('.t-cell.th').forEach(h => h.setAttribute('aria-sort', 'none'));
            btn.setAttribute('aria-sort', sortDir === 'asc' ? 'ascending' : 'descending');
            renderTable();
        });
    });

    document.getElementById('range')?.addEventListener('change', load);

    // Обработка экспорта с фильтрами
    document.getElementById('btn-export')?.addEventListener('click', () => {
        const dateFrom = document.getElementById('export-date-from')?.value || '';
        const dateTo = document.getElementById('export-date-to')?.value || '';
        
        let url = '/admin/api/analytics/export.xlsx';
        const params = new URLSearchParams();
        
        if (dateFrom) params.append('date_from', dateFrom);
        if (dateTo) params.append('date_to', dateTo);
        
        if (params.toString()) {
            url += '?' + params.toString();
        }
        
        window.location.href = url;
    });

    load();
})();


