// static/script/inbox.js
function getCsrf() {
    const m = document.cookie.match(/csrftoken=([^;]+)/);
    return m ? m[1] : '';
}

function showToast(msg, isError = false) {
    const t = document.getElementById('toast');
    t.textContent = msg;
    t.classList.toggle('error', isError);
    t.classList.add('show');
    setTimeout(() => t.classList.remove('show'), 2800);
}

// ── Webhook info box ──────────────────────────────────────────────────────
document.getElementById('openWebhookInfo')?.addEventListener('click', () => {
    document.getElementById('webhookBox').classList.toggle('open');
});

document.getElementById('copyWebhookBtn')?.addEventListener('click', async () => {
    const url = document.getElementById('webhookUrl').textContent.trim();
    try {
        await navigator.clipboard.writeText(url);
        showToast("Manzil nusxalandi ✓");
    } catch {
        showToast("Nusxalashda xatolik", true);
    }
});

document.getElementById('regenTokenBtn')?.addEventListener('click', async () => {
    if (!confirm("Eski manzil ishlamay qoladi va MacroDroid'da yangisini qo'yishingiz kerak bo'ladi. Davom etamizmi?")) return;
    try {
        const resp = await fetch("/inbox/regenerate-token/", {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrf() },
        });
        const data = await resp.json();
        if (data.status === 'success') {
            document.getElementById('webhookUrl').textContent = data.webhook_url;
            showToast("Yangi manzil yaratildi ✓");
        }
    } catch {
        showToast("Xatolik yuz berdi", true);
    }
});

// ── Match modal ─────────────────────────────────────────────────────────
let currentTxnId = null;

document.querySelectorAll('.txn-btn.match').forEach(btn => {
    btn.addEventListener('click', () => {
        currentTxnId = btn.dataset.id;
        document.getElementById('matchAmount').value = btn.dataset.amount || '';
        document.getElementById('clientSearch').value = '';
        document.getElementById('matchError').classList.add('d-none');
        filterClients('');
        document.getElementById('matchModal').classList.remove('d-none');
    });
});

document.querySelectorAll('.txn-btn.ignore').forEach(btn => {
    btn.addEventListener('click', async () => {
        if (!confirm("Bu tushumga e'tibor berilmasin (spam/aloqasi yo'q)?")) return;
        const id = btn.dataset.id;
        const resp = await fetch(`/inbox/${id}/ignore/`, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrf() },
        });
        if (resp.ok) {
            document.getElementById(`txn-${id}`)?.remove();
            showToast("E'tiborsiz qoldirildi");
        }
    });
});

function filterClients(query) {
    query = query.toLowerCase().trim();
    document.querySelectorAll('#clientSelect option').forEach(opt => {
        const matches = !query || (opt.dataset.search || '').includes(query);
        opt.style.display = matches ? '' : 'none';
    });
}

document.getElementById('clientSearch')?.addEventListener('input', (e) => {
    filterClients(e.target.value);
});

document.querySelectorAll('[data-close]').forEach(btn => {
    btn.addEventListener('click', () => document.getElementById(btn.dataset.close).classList.add('d-none'));
});

document.getElementById('matchForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const clientId = document.getElementById('clientSelect').value;
    const amount = document.getElementById('matchAmount').value;
    const errBox = document.getElementById('matchError');

    if (!clientId) {
        errBox.textContent = "Mijozni tanlang";
        errBox.classList.remove('d-none');
        return;
    }

    const resp = await fetch(`/inbox/${currentTxnId}/match/`, {
        method: 'POST',
        headers: { 'X-CSRFToken': getCsrf() },
        body: new URLSearchParams({ client_id: clientId, amount: amount }),
    });
    const data = await resp.json();

    if (data.status === 'success') {
        document.getElementById('matchModal').classList.add('d-none');
        document.getElementById(`txn-${currentTxnId}`)?.remove();
        showToast("To'lov yaratildi ✓");
    } else {
        errBox.textContent = data.message || 'Xatolik yuz berdi';
        errBox.classList.remove('d-none');
    }
});
