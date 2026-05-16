/* ═══════════════════════════════════════════════════════════════
   staff.js  —  Xodimlar boshqaruvi
   ═══════════════════════════════════════════════════════════════ */

'use strict';

// ── CSRF TOKEN ────────────────────────────────────────────────────────────────
function getCsrf() {
    return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
}

// ── TOAST ─────────────────────────────────────────────────────────────────────
const toast = document.getElementById('toast');
let toastTimer;

function showToast(msg, type = 'success') {
    clearTimeout(toastTimer);
    toast.textContent = msg;
    toast.className = `toast show ${type}`;
    toastTimer = setTimeout(() => toast.classList.remove('show'), 3200);
}

// ── MODAL ─────────────────────────────────────────────────────────────────────
function openModal(id) {
    document.getElementById(id)?.classList.remove('d-none');
}

function closeModal(id) {
    document.getElementById(id)?.classList.add('d-none');
}

// Close buttons  [data-close="modalId"]
document.querySelectorAll('[data-close]').forEach(btn => {
    btn.addEventListener('click', () => closeModal(btn.dataset.close));
});

// Overlay click → close
document.querySelectorAll('.modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', e => {
        if (e.target === overlay) closeModal(overlay.id);
    });
});

// ── TABS ──────────────────────────────────────────────────────────────────────
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        const tab = btn.dataset.tab;
        document.querySelectorAll('.staff-section').forEach(s => s.classList.add('d-none'));
        document.getElementById(`tab-${tab}`)?.classList.remove('d-none');
    });
});

// ── PASSWORD TOGGLE ───────────────────────────────────────────────────────────
document.querySelectorAll('.pass-toggle').forEach(btn => {
    btn.addEventListener('click', () => {
        const inp = document.getElementById(btn.dataset.target);
        if (!inp) return;
        const isPass = inp.type === 'password';
        inp.type = isPass ? 'text' : 'password';
        btn.querySelector('i').className = isPass ? 'fa fa-eye-slash' : 'fa fa-eye';
    });
});

// ── STATS UPDATE ──────────────────────────────────────────────────────────────
function updateStats() {
    const activeCount = document.querySelectorAll('#tab-active .staff-card').length;
    const firedCount  = document.querySelectorAll('#tab-fired .staff-card').length;

    document.querySelectorAll('.active-count').forEach(el => el.textContent = activeCount);
    document.querySelectorAll('.fired-count').forEach(el => el.textContent  = firedCount);
    document.querySelectorAll('.total-count').forEach(el => el.textContent  = activeCount + firedCount);

    // Tab badge counts
    document.querySelectorAll('.tab-btn').forEach(btn => {
        const count = btn.dataset.tab === 'active' ? activeCount : firedCount;
        const badge = btn.querySelector('.tab-count');
        if (badge) badge.textContent = count;
    });
}

// ── FORM ERROR HELPER ─────────────────────────────────────────────────────────
function showFormError(errorElId, errors) {
    const el = document.getElementById(errorElId);
    if (!el) return;

    let html = '';
    if (typeof errors === 'string') {
        html = errors;
    } else {
        // Django form.errors — object of field: [messages]
        html = Object.entries(errors)
            .map(([field, msgs]) => {
                const label = field === '__all__' ? '' : `<b>${field}:</b> `;
                return `<div>${label}${Array.isArray(msgs) ? msgs.join(', ') : msgs}</div>`;
            })
            .join('');
    }

    el.innerHTML = html;
    el.classList.remove('d-none');
}

function clearFormError(errorElId) {
    const el = document.getElementById(errorElId);
    if (!el) return;
    el.textContent = '';
    el.classList.add('d-none');
}

// ── URL BUILDER ───────────────────────────────────────────────────────────────
function buildUrl(template, id) {
    // template: "/accounts/staff/0/edit/"  → replace 0 with actual id
    return template.replace('/0/', `/${id}/`);
}

// ══════════════════════════════════════════════════════════════════════════════
//  ADD STAFF
// ══════════════════════════════════════════════════════════════════════════════
document.getElementById('openAddStaff')?.addEventListener('click', () => {
    document.getElementById('addStaffForm')?.reset();
    clearFormError('addError');
    openModal('addModal');
});

document.getElementById('addStaffForm')?.addEventListener('submit', async e => {
    e.preventDefault();
    clearFormError('addError');

    const form    = e.target;
    const btn     = form.querySelector('[type=submit]');
    const origTxt = btn.innerHTML;
    btn.disabled  = true;
    btn.innerHTML = '<i class="fa fa-spinner fa-spin"></i> Saqlanmoqda...';

    try {
        const res  = await fetch(window.STAFF_URLS.create, {
            method:  'POST',
            headers: { 'X-CSRFToken': getCsrf() },
            body:    new FormData(form),
        });
        const data = await res.json();

        if (data.status === 'created') {
            closeModal('addModal');
            showToast(`✅ ${data.username} qo'shildi!`);
            appendActiveCard(data);
            updateStats();
            form.reset();
        } else {
            showFormError('addError', data.errors || data.message || 'Xatolik yuz berdi');
        }
    } catch {
        showFormError('addError', 'Server bilan bog\'lanishda xatolik');
    } finally {
        btn.disabled  = false;
        btn.innerHTML = origTxt;
    }
});

// ── Build & append card to Active list ───────────────────────────────────────
function appendActiveCard(data) {
    const list = document.querySelector('#tab-active .staff-list');
    if (!list) return;

    // Remove empty-state if present
    list.querySelector('.empty-state')?.remove();

    const initials = data.username.slice(0, 2).toUpperCase();
    const roleLabel = data.role_display || data.role;

    const card = document.createElement('div');
    card.className = 'staff-card';
    card.id = `staff-${data.id}`;
    card.dataset.id       = data.id;
    card.dataset.username = data.username;
    card.dataset.phone    = data.phone || '';
    card.dataset.role     = data.role;

    card.innerHTML = `
        <div class="sc-avatar ${data.role}">${initials}</div>
        <div class="sc-info">
            <div class="sc-name">${data.username}</div>
            <div class="sc-meta">
                <span class="role-badge ${data.role}">${roleLabel}</span>
                ${data.phone ? `<span class="sc-phone"><i class="fa fa-phone"></i> ${data.phone}</span>` : ''}
            </div>
            <div class="sc-date">
                <i class="fa fa-calendar"></i> Bugun qo'shildi
            </div>
        </div>
        <div class="sc-actions">
            <button class="sca-btn edit"
                    data-id="${data.id}"
                    data-username="${data.username}"
                    data-phone="${data.phone || ''}"
                    data-role="${data.role}"
                    title="Tahrirlash">
                <i class="fa fa-pen"></i>
            </button>
            <button class="sca-btn fire"
                    data-id="${data.id}"
                    data-username="${data.username}"
                    title="Ishdan haydash">
                <i class="fa fa-user-slash"></i>
            </button>
        </div>
    `;
    list.prepend(card);
}

// ══════════════════════════════════════════════════════════════════════════════
//  EDIT STAFF  (event delegation)
// ══════════════════════════════════════════════════════════════════════════════
document.addEventListener('click', e => {
    const editBtn = e.target.closest('.sca-btn.edit');
    if (!editBtn) return;

    const { id, username, phone, role } = editBtn.dataset;

    document.getElementById('editUserId').value    = id;
    document.getElementById('editUsername').value  = username;
    document.getElementById('editPhone').value     = phone || '';
    const roleSelect = document.getElementById('editRole');
    if (roleSelect) roleSelect.value = role;

    clearFormError('editError');
    openModal('editModal');
});

document.getElementById('editStaffForm')?.addEventListener('submit', async e => {
    e.preventDefault();
    clearFormError('editError');

    const form    = e.target;
    const userId  = document.getElementById('editUserId').value;
    const btn     = form.querySelector('[type=submit]');
    const origTxt = btn.innerHTML;
    btn.disabled  = true;
    btn.innerHTML = '<i class="fa fa-spinner fa-spin"></i> Saqlanmoqda...';

    const url = buildUrl(window.STAFF_URLS.edit, userId);

    try {
        const res  = await fetch(url, {
            method:  'POST',
            headers: { 'X-CSRFToken': getCsrf() },
            body:    new FormData(form),
        });
        const data = await res.json();

        if (data.status === 'updated') {
            closeModal('editModal');
            showToast(`✏️ ${data.username} tahrirlandi`);
            updateCardUI(userId, data);
        } else {
            showFormError('editError', data.errors || data.message || 'Xatolik');
        }
    } catch {
        showFormError('editError', 'Server bilan bog\'lanishda xatolik');
    } finally {
        btn.disabled  = false;
        btn.innerHTML = origTxt;
    }
});

// ── Update card data & display after edit ────────────────────────────────────
function updateCardUI(userId, data) {
    const card = document.getElementById(`staff-${userId}`);
    if (!card) return;

    // Update data attributes
    card.dataset.username = data.username;
    card.dataset.phone    = data.phone || '';
    card.dataset.role     = data.role || card.dataset.role;

    // Update name
    const nameEl = card.querySelector('.sc-name');
    if (nameEl) nameEl.textContent = data.username;

    // Update role badge
    const badge = card.querySelector('.role-badge');
    if (badge && data.role) {
        badge.className   = `role-badge ${data.role}`;
        badge.textContent = data.role_display || data.role;
    }

    // Update avatar initials
    const avatar = card.querySelector('.sc-avatar');
    if (avatar) {
        avatar.className  = `sc-avatar ${data.role || card.dataset.role}`;
        avatar.textContent = data.username.slice(0, 2).toUpperCase();
    }

    // Update phone
    const phoneMeta = card.querySelector('.sc-phone');
    if (data.phone) {
        if (phoneMeta) {
            phoneMeta.innerHTML = `<i class="fa fa-phone"></i> ${data.phone}`;
        } else {
            const metaDiv = card.querySelector('.sc-meta');
            if (metaDiv) {
                const sp = document.createElement('span');
                sp.className = 'sc-phone';
                sp.innerHTML = `<i class="fa fa-phone"></i> ${data.phone}`;
                metaDiv.appendChild(sp);
            }
        }
    } else if (phoneMeta) {
        phoneMeta.remove();
    }

    // Sync edit button data
    const editBtn = card.querySelector('.sca-btn.edit');
    if (editBtn) {
        editBtn.dataset.username = data.username;
        editBtn.dataset.phone    = data.phone || '';
        editBtn.dataset.role     = data.role || card.dataset.role;
    }

    // Sync fire button data
    const fireBtn = card.querySelector('.sca-btn.fire');
    if (fireBtn) fireBtn.dataset.username = data.username;
}

// ══════════════════════════════════════════════════════════════════════════════
//  FIRE STAFF  (event delegation → confirm modal)
// ══════════════════════════════════════════════════════════════════════════════
let pendingAction = null; // { userId, action, username }

document.addEventListener('click', e => {
    const fireBtn = e.target.closest('.sca-btn.fire');
    if (!fireBtn) return;

    const { id, username } = fireBtn.dataset;
    pendingAction = { userId: id, action: 'fire', username };

    document.getElementById('confirmTitle').textContent = 'Ishdan haydash';
    document.getElementById('confirmText').textContent  =
        `"${username}" ni ishdan haydashni tasdiqlaysizmi?`;
    document.getElementById('confirmOk').className = 'btn-danger';
    document.getElementById('confirmOk').textContent = 'Haydash';

    openModal('confirmModal');
});

// ── RESTORE STAFF ─────────────────────────────────────────────────────────────
document.addEventListener('click', e => {
    const restoreBtn = e.target.closest('.sca-btn.restore');
    if (!restoreBtn) return;

    const { id, username } = restoreBtn.dataset;
    pendingAction = { userId: id, action: 'restore', username };

    document.getElementById('confirmTitle').textContent = 'Qayta yollash';
    document.getElementById('confirmText').textContent  =
        `"${username}" ni qayta yollashni tasdiqlaysizmi?`;
    document.getElementById('confirmOk').className = 'btn-submit';
    document.getElementById('confirmOk').textContent = 'Yollash';

    openModal('confirmModal');
});

// ── Confirm OK button ─────────────────────────────────────────────────────────
document.getElementById('confirmOk')?.addEventListener('click', async () => {
    if (!pendingAction) return;

    const { userId, action, username } = pendingAction;
    pendingAction = null;
    closeModal('confirmModal');

    const url  = buildUrl(window.STAFF_URLS.fire, userId);
    const body = new FormData();
    body.append('action', action);
    body.append('csrfmiddlewaretoken', getCsrf());

    try {
        const res  = await fetch(url, {
            method:  'POST',
            headers: { 'X-CSRFToken': getCsrf() },
            body,
        });
        const data = await res.json();

        if (data.status === 'success') {
            if (action === 'fire') {
                showToast(`🚫 ${username} ishdan haydalDi`, 'warning');
                moveToFired(userId, username);
            } else {
                showToast(`✅ ${username} qayta yollandi`);
                moveToActive(userId, username);
            }
            updateStats();
        } else {
            showToast(data.message || 'Xatolik yuz berdi', 'error');
        }
    } catch {
        showToast('Server bilan bog\'lanishda xatolik', 'error');
    }
});

// ── Move card Active → Fired ──────────────────────────────────────────────────
function moveToFired(userId, username) {
    const card = document.getElementById(`staff-${userId}`);
    if (!card) return;

    // Remove from active
    card.remove();

    // Add empty state if no active left
    const activeList = document.querySelector('#tab-active .staff-list');
    if (activeList && !activeList.querySelector('.staff-card')) {
        activeList.innerHTML = `
            <div class="empty-state">
                <div class="es-icon"><i class="fa fa-users"></i></div>
                <p>Faol xodimlar yo'q</p>
            </div>`;
    }

    // Build fired card
    const firedList = document.querySelector('#tab-fired .staff-list');
    if (!firedList) return;
    firedList.querySelector('.empty-state')?.remove();

    const initials = username.slice(0, 2).toUpperCase();
    const firedCard = document.createElement('div');
    firedCard.className = 'staff-card fired';
    firedCard.id = `staff-${userId}`;
    firedCard.dataset.id       = userId;
    firedCard.dataset.username = username;

    const today = new Date().toLocaleDateString('uz-UZ', {
        day: '2-digit', month: '2-digit', year: 'numeric'
    }).replace(/\//g, '.');

    firedCard.innerHTML = `
        <div class="sc-avatar fired">${initials}</div>
        <div class="sc-info">
            <div class="sc-name fired-name">${username}</div>
            <div class="sc-meta">
                <span class="role-badge fired">Haydalgan</span>
                <span class="fired-date">
                    <i class="fa fa-calendar-xmark"></i> ${today}
                </span>
            </div>
        </div>
        <div class="sc-actions">
            <button class="sca-btn restore"
                    data-id="${userId}"
                    data-username="${username}"
                    title="Qayta yollash">
                <i class="fa fa-rotate-left"></i>
            </button>
        </div>
    `;
    firedList.prepend(firedCard);
}

// ── Move card Fired → Active ──────────────────────────────────────────────────
function moveToActive(userId, username) {
    const card = document.getElementById(`staff-${userId}`);
    if (!card) return;

    card.remove();

    const firedList = document.querySelector('#tab-fired .staff-list');
    if (firedList && !firedList.querySelector('.staff-card')) {
        firedList.innerHTML = `
            <div class="empty-state">
                <div class="es-icon"><i class="fa fa-check-circle"></i></div>
                <p>Haydalgan xodimlar yo'q</p>
            </div>`;
    }

    const activeList = document.querySelector('#tab-active .staff-list');
    if (!activeList) return;
    activeList.querySelector('.empty-state')?.remove();

    const initials = username.slice(0, 2).toUpperCase();
    const newCard = document.createElement('div');
    newCard.className = 'staff-card';
    newCard.id = `staff-${userId}`;
    newCard.dataset.id       = userId;
    newCard.dataset.username = username;
    newCard.dataset.phone    = '';
    newCard.dataset.role     = 'staff';

    newCard.innerHTML = `
        <div class="sc-avatar staff">${initials}</div>
        <div class="sc-info">
            <div class="sc-name">${username}</div>
            <div class="sc-meta">
                <span class="role-badge staff">Xodim</span>
            </div>
            <div class="sc-date">
                <i class="fa fa-calendar"></i> Qayta yollandi
            </div>
        </div>
        <div class="sc-actions">
            <button class="sca-btn edit"
                    data-id="${userId}"
                    data-username="${username}"
                    data-phone=""
                    data-role="staff"
                    title="Tahrirlash">
                <i class="fa fa-pen"></i>
            </button>
            <button class="sca-btn fire"
                    data-id="${userId}"
                    data-username="${username}"
                    title="Ishdan haydash">
                <i class="fa fa-user-slash"></i>
            </button>
        </div>
    `;
    activeList.prepend(newCard);
}