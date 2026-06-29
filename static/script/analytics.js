// static/script/analytics.js
// "Analitika" sahifasi — Sotuv (accrual) va Kassa (cash) ni alohida ko'rsatadi.

function fmtMoney(n) {
    n = Number(n) || 0;
    return Math.round(n).toLocaleString('uz-UZ').replace(/,/g, ' ') + " so'm";
}

function setText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
}

let trendChartInstance = null;

function renderNarrative(text) {
    setText('narrativeText', text);
}

function renderFlow(period) {
    setText('flowSales',   fmtMoney(period.sales_accrual));
    setText('flowCashIn',  fmtMoney(period.cash_in));
    setText('flowCashOut', fmtMoney(period.cash_out_supplier));
    const net = period.net_cash_flow;
    setText('flowNetCash', (net >= 0 ? '+' : '') + fmtMoney(net));
    setText('flowCollectedPct', `${period.collected_percent}% yig'ildi`);

    const netCard = document.getElementById('flowNetCash')?.closest('.flow-card');
    if (netCard) {
        netCard.classList.toggle('negative', net < 0);
    }
}

function renderDebt(debt) {
    setText('debtReceivables', fmtMoney(debt.receivables));
    setText('debtPayables',    fmtMoney(debt.payables));

    const total = Math.max(debt.receivables + debt.payables, 1);
    const recvPct = (debt.receivables / total * 100).toFixed(1);
    const payPct  = (debt.payables    / total * 100).toFixed(1);
    const recvBar = document.getElementById('debtBarReceivables');
    const payBar  = document.getElementById('debtBarPayables');
    if (recvBar) recvBar.style.width = recvPct + '%';
    if (payBar)  payBar.style.width  = payPct + '%';

    const netEl = document.getElementById('debtNet');
    if (netEl) {
        if (debt.net >= 0) {
            netEl.innerHTML = `<i class="fa fa-circle-check"></i> Sof holat ijobiy: mijozlardan kutilayotgan pul ta'minotchiga qarzdan <strong>${fmtMoney(debt.net)}</strong> ko'p`;
            netEl.classList.remove('warn');
        } else {
            netEl.innerHTML = `<i class="fa fa-triangle-exclamation"></i> Diqqat: ta'minotchiga qarz mijozlardan kutilayotgan summadan <strong>${fmtMoney(Math.abs(debt.net))}</strong> ko'p`;
            netEl.classList.add('warn');
        }
    }
}

function renderAging(buckets) {
    const wrap = document.getElementById('agingList');
    if (!wrap) return;
    const maxAmount = Math.max(...buckets.map(b => b.amount), 1);

    wrap.innerHTML = buckets.map(b => {
        const pct = (b.amount / maxAmount * 100).toFixed(1);
        const isOld = b.label.includes('90');
        return `
            <div class="aging-row">
                <div class="aging-label">${b.label}</div>
                <div class="aging-bar-track">
                    <div class="aging-bar-fill ${isOld ? 'danger' : ''}" style="width:${pct}%"></div>
                </div>
                <div class="aging-amount">${fmtMoney(b.amount)}</div>
                <div class="aging-count">${b.count} mijoz</div>
            </div>`;
    }).join('');
}

function renderTrendChart(trend) {
    const canvas = document.getElementById('trendChart');
    if (!canvas) return;
    if (trendChartInstance) trendChartInstance.destroy();

    trendChartInstance = new Chart(canvas.getContext('2d'), {
        type: 'bar',
        data: {
            labels: trend.labels,
            datasets: [
                {
                    label: 'Sotilgan (accrual)',
                    data: trend.sales,
                    backgroundColor: 'rgba(34,211,238,0.55)',
                    borderRadius: 6,
                },
                {
                    label: 'Mijozdan kelgan (cash in)',
                    data: trend.cash_in,
                    backgroundColor: 'rgba(0,229,160,0.65)',
                    borderRadius: 6,
                },
                {
                    label: "Ta'minotchiga to'langan (cash out)",
                    data: trend.cash_out,
                    backgroundColor: 'rgba(255,85,114,0.55)',
                    borderRadius: 6,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'bottom', labels: { color: '#a8b0c0', font: { size: 11 } } },
            },
            scales: {
                x: { ticks: { color: '#a8b0c0' }, grid: { color: 'rgba(255,255,255,0.04)' } },
                y: { ticks: { color: '#a8b0c0' }, grid: { color: 'rgba(255,255,255,0.04)' } },
            },
        },
    });
}

async function loadAnalytics() {
    const loader = document.getElementById('pageLoader');
    try {
        const res = await fetch(window.ANALYTICS_URLS.analyticsApi, {
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
        });
        if (!res.ok) throw new Error('Server xatosi: ' + res.status);
        const data = await res.json();

        // Har bir blokni alohida render qilamiz — biri xato bersa
        // (masalan Chart.js CDN yuklanmasa), qolganlari ko'rinishda qoladi.
        try { renderNarrative(data.narrative); } catch (e) { console.error('narrative:', e); }
        try { renderFlow(data.period); } catch (e) { console.error('flow:', e); }
        try { renderDebt(data.debt_position); } catch (e) { console.error('debt:', e); }
        try { renderAging(data.aging); } catch (e) { console.error('aging:', e); }
        try {
            if (typeof Chart === 'undefined') throw new Error('Chart.js yuklanmadi (internet/CDN tekshiring)');
            renderTrendChart(data.trend);
        } catch (e) {
            console.error('trend chart:', e);
            const wrap = document.querySelector('.chart-wrap');
            if (wrap) wrap.innerHTML = `<div class="chart-error">Grafikni yuklab bo'lmadi: ${e.message}</div>`;
        }
    } catch (e) {
        renderNarrative("Ma'lumotlarni yuklab bo'lmadi: " + e.message);
    } finally {
        if (loader) loader.classList.add('hidden');
    }
}

document.addEventListener('DOMContentLoaded', loadAnalytics);
