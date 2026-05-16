'use strict';

// ── UTILS ─────────────────────────────────────────────────────────────────────

function fmt(n) {
    if (n === null || n === undefined || isNaN(Number(n))) return '0';
    const num = Number(n);
    const abs = Math.abs(num);
    const sign = num < 0 ? '-' : '';
    if (abs >= 1_000_000_000) return sign + (abs / 1_000_000_000).toFixed(1) + ' mlrd';
    if (abs >= 1_000_000)     return sign + (abs / 1_000_000).toFixed(1)     + ' mln';
    if (abs >= 1_000)         return sign + (abs / 1_000).toFixed(1)         + ' ming';
    return num.toLocaleString('uz-UZ');
}

function fmtFull(n) {
    if (!n) return '0';
    return Number(n).toLocaleString('uz-UZ') + ' so\'m';
}

function setText(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
}

// ── DATE ──────────────────────────────────────────────────────────────────────

const dateEl = document.getElementById('currentDate');
if (dateEl) {
    const now = new Date();
    dateEl.textContent = now.toLocaleDateString('uz-UZ', {
        weekday: 'short', year: 'numeric', month: 'short', day: 'numeric'
    }).toUpperCase();
}

// ── CHART ─────────────────────────────────────────────────────────────────────

const ctx   = document.getElementById('smartChart')?.getContext('2d');
let chart   = null;
let allData = null;
let period  = 'weekly';

const C = {
    green: '#00e5a0',
    cyan:  '#22d3ee',
    blue:  '#6366f1',
    red:   '#ff5572',
};

function makeDS(label, data, color, fill = 'rgba(0,0,0,0)') {
    return {
        label,
        data,
        borderColor:     color,
        backgroundColor: fill,
        borderWidth: 2,
        pointRadius: 3,
        pointHoverRadius: 7,
        pointBackgroundColor: color,
        tension: 0.45,
        fill: true,
    };
}

function buildChart(pd) {
    if (!ctx) return;
    const { labels, profits = [], expenses = [], payments = [], sales = [] } = pd;

    if (chart) chart.destroy();

    chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [
                makeDS('Foyda',   profits,  C.green,  'rgba(0,229,160,0.06)'),
                makeDS('Sotuv',   sales,    C.cyan,   'rgba(34,211,238,0.04)'),
                makeDS('To\'lov', payments, C.blue,   'rgba(99,102,241,0.04)'),
                makeDS('Harajat', expenses, C.red,    'rgba(255,85,114,0.04)'),
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            animation: { duration: 600, easing: 'easeInOutQuart' },
            plugins: {
                legend: {
                    display: false,
                },
                tooltip: {
                    backgroundColor: '#090d18',
                    borderColor: '#141f35',
                    borderWidth: 1,
                    titleColor: '#6b84a8',
                    bodyColor: '#dde6f8',
                    padding: 12,
                    callbacks: {
                        label: ctx =>
                            ` ${ctx.dataset.label}: ${fmt(ctx.parsed.y)} so'm`,
                    },
                },
            },
            scales: {
                x: {
                    ticks: {
                        color: '#2d4060',
                        font: { family: "'Space Mono'", size: 10 }
                    },
                    grid: { color: 'rgba(20,31,53,0.8)' },
                    border: { color: '#141f35' },
                },
                y: {
                    ticks: {
                        color: '#2d4060',
                        font: { family: "'Space Mono'", size: 10 },
                        callback: v => fmt(v),
                    },
                    grid: { color: 'rgba(20,31,53,0.8)' },
                    border: { color: '#141f35' },
                },
            },
        },
    });

    // Update summaries
    const sum = arr => arr.reduce((a, b) => a + Number(b || 0), 0);
    const totalProfit = sum(profits);
    const profitSumEl = document.getElementById('sum-profit');
    if (profitSumEl) {
        profitSumEl.textContent = fmt(totalProfit) + ' so\'m';
        profitSumEl.style.color = totalProfit < 0 ? 'var(--red, #ff5572)' : '';
    }
    setText('sum-expense', fmt(sum(expenses)) + ' so\'m');
    setText('sum-payment', fmt(sum(payments)) + ' so\'m');
    setText('sum-sale',    fmt(sum(sales))    + ' so\'m');
}

// ── PERIOD SWITCHER ───────────────────────────────────────────────────────────

document.querySelectorAll('.pt-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        if (!allData) return;
        period = btn.dataset.period;

        document.querySelectorAll('.pt-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        buildChart(allData.chart[period]);
    });
});

// ── KPI CARDS ─────────────────────────────────────────────────────────────────

function animateKPI(id, value, barId, fillPct = 75) {
    const el = document.getElementById(id);
    if (!el) return;

    const target  = Number(value) || 0;
    const isNeg   = target < 0;
    const start   = Date.now();
    const dur     = 900;

    // Minus bo'lsa element rangini o'zgartirish
    if (isNeg) {
        el.style.color = 'var(--red, #ff5572)';
        const card = document.getElementById(barId);
        if (card) card.style.borderColor = 'rgba(255,85,114,0.2)';
    } else {
        el.style.color = '';
    }

    function tick() {
        const elapsed  = Date.now() - start;
        const progress = Math.min(elapsed / dur, 1);
        const ease     = 1 - Math.pow(1 - progress, 3);
        const current  = target * ease;
        el.textContent = fmt(current) + ' so\'m';
        if (progress < 1) requestAnimationFrame(tick);
        else el.textContent = fmt(target) + ' so\'m';
    }
    requestAnimationFrame(tick);

    // Bar — minus bo'lsa qizil
    const fill = document.querySelector(`#${barId} .kpi-fill`);
    if (fill) {
        if (isNeg) fill.style.background = 'var(--red, #ff5572)';
        setTimeout(() => { fill.style.width = fillPct + '%'; }, 200);
    }
}

function renderKPI(year) {
    const values = [
        { valId: 'profit-year',  cardId: 'kpi-profit',  val: year.profit,  pct: 85 },
        { valId: 'sale-year',    cardId: 'kpi-sale',    val: year.sale,    pct: 100 },
        { valId: 'payment-year', cardId: 'kpi-payment', val: year.payment, pct: 70 },
        { valId: 'expense-year', cardId: 'kpi-expense', val: year.expense, pct: 60 },
    ];

    const maxVal = Math.max(...values.map(v => Number(v.val) || 0)) || 1;
    values.forEach(({ valId, cardId, val }) => {
        const pct = Math.round((Number(val) / maxVal) * 100);
        animateKPI(valId, val, cardId, pct);
    });

    // Potensial foyda (sotuv - harajat, qarz ham kiritilgan)
    const grossEl = document.getElementById('gross-profit-year');
    if (grossEl && year.gross_profit !== undefined) {
        grossEl.textContent = fmt(year.gross_profit) + ' so\'m';
    }
}

// ── TOP PRODUCTS ──────────────────────────────────────────────────────────────

function renderProducts(products) {
    const container = document.getElementById('productsList');
    if (!container) return;

    const badge = document.getElementById('topProductsBadge');
    if (badge) badge.textContent = (products?.length || 0) + ' ta';

    if (!products || products.length === 0) {
        container.innerHTML = `
            <div style="text-align:center;padding:40px 0;color:var(--text-3);font-size:0.82rem">
                Ma'lumot yo'q
            </div>`;
        return;
    }

    const maxRev = Math.max(...products.map(p => Number(p.revenue) || 0)) || 1;

    const rankIcons = ['🥇', '🥈', '🥉'];
    const rankClasses = ['top1', 'top2', 'top3'];

    container.innerHTML = products.map((p, i) => {
        const barPct = Math.round((Number(p.revenue) / maxRev) * 100);
        const rankCls = rankClasses[i] || '';
        const rankLabel = rankIcons[i] || `#${i + 1}`;

        return `
        <div class="product-row">
            <div class="pr-rank ${rankCls}">${rankLabel}</div>
            <div class="pr-info">
                <div class="pr-name">${p.name}</div>
                <div class="pr-cat">${p.category || '—'}</div>
            </div>
            <div class="pr-bar-wrap">
                <div class="pr-bar-track">
                    <div class="pr-bar-fill" style="width:${barPct}%"></div>
                </div>
            </div>
            <div class="pr-stats">
                <div class="pr-revenue">${fmt(p.revenue)} so'm</div>
                <div class="pr-sold">${p.sold} dona · ${fmt(p.profit)} foyda</div>
            </div>
        </div>`;
    }).join('');
}

// ── TODAY SNAPSHOT ────────────────────────────────────────────────────────────

function renderToday(today) {
    // API dan to'g'ridan to'g'ri bugungi ma'lumot
    if (!today) return;

    const now = new Date();
    const label = now.toLocaleDateString('uz-UZ', { day:'2-digit', month:'2-digit' });
    const todayLabel = document.getElementById('todayLabel');
    if (todayLabel) todayLabel.textContent = label;

    // Today - minus bo'lsa qizil rang
    const profitEl = document.getElementById('today-profit');
    if (profitEl) {
        profitEl.textContent = fmt(today.profit) + ' so\'m';
        profitEl.style.color = today.profit < 0
            ? 'var(--red, #ff5572)'
            : 'var(--green, #00e5a0)';
    }
    setText('today-sale',    fmt(today.sale)    + ' so\'m');
    setText('today-payment', fmt(today.payment) + ' so\'m');
    setText('today-expense', fmt(today.expense) + ' so\'m');
}

// ── CACHE INFO ────────────────────────────────────────────────────────────────

function updateCacheInfo() {
    const now = new Date();
    const timeStr = now.toLocaleTimeString('uz-UZ', { hour: '2-digit', minute: '2-digit' });
    setText('lastUpdate', timeStr + ' da yangilandi');
}

// ── MAIN FETCH ────────────────────────────────────────────────────────────────

async function loadDashboard() {
    const loader = document.getElementById('pageLoader');

    try {
        const res = await fetch(window.DASHBOARD_URLS.dashboardApi, {
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        });

        if (!res.ok) throw new Error('Server xatosi: ' + res.status);

        allData = await res.json();

        // Render all
        renderKPI(allData.year);
        renderProducts(allData.top_products);
        buildChart(allData.chart[period]);
        renderToday(allData.today);
        updateCacheInfo();

        // Hide loader
        if (loader) {
            loader.classList.add('hidden');
            setTimeout(() => { loader.style.display = 'none'; }, 400);
        }

    } catch (err) {
        console.error('Dashboard yuklashda xatolik:', err);
        if (loader) {
            loader.innerHTML = `
                <div class="loader-inner">
                    <div style="color:#ff5572;font-size:1.5rem"><i class="fa fa-exclamation-triangle"></i></div>
                    <div style="color:#6b84a8;font-size:0.8rem;font-family:'Space Mono'">
                        Ma'lumot yuklanmadi. Sahifani yangilang.
                    </div>
                    <button onclick="location.reload()"
                            style="margin-top:10px;background:#0d1525;border:1px solid #141f35;
                                   color:#dde6f8;padding:8px 20px;border-radius:6px;cursor:pointer;
                                   font-family:'Space Grotesk'">
                        Qayta urinish
                    </button>
                </div>`;
        }
    }
}

document.addEventListener('DOMContentLoaded', loadDashboard);