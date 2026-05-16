'use strict';

// ── TOAST ─────────────────────────────────────────────────────────────────────
function toast(msg, type = 'success', ms = 3000) {
    const el = document.getElementById('toast');
    if (!el) return;
    el.textContent = msg;
    el.className = `toast-el ${type} show`;
    clearTimeout(el._t);
    el._t = setTimeout(() => { el.className = 'toast-el'; }, ms);
}

// ── CSRF ──────────────────────────────────────────────────────────────────────
function csrf() {
    return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
}

// ── MODAL ─────────────────────────────────────────────────────────────────────
function openModal(id) {
    document.getElementById(id)?.classList.remove('d-none');
}

function closeModal(id) {
    document.getElementById(id)?.classList.add('d-none');
}

// Overlay click → close
document.querySelectorAll('.modal-veil').forEach(veil => {
    veil.addEventListener('click', e => {
        if (e.target === veil) veil.classList.add('d-none');
    });
});

// data-close buttons
document.querySelectorAll('[data-close]').forEach(btn => {
    btn.addEventListener('click', () => closeModal(btn.dataset.close));
});

// ── ERROR ─────────────────────────────────────────────────────────────────────
function showErr(elId, errors) {
    const el = document.getElementById(elId);
    if (!el) return;
    const msg = typeof errors === 'string'
        ? errors
        : Object.entries(errors)
            .map(([k, v]) => Array.isArray(v) ? v.join(', ') : v)
            .join(' · ');
    el.innerHTML = msg;
    el.classList.remove('d-none');
}

function clearErr(elId) {
    const el = document.getElementById(elId);
    if (el) { el.innerHTML = ''; el.classList.add('d-none'); }
}

// ── COUNT UPDATER ─────────────────────────────────────────────────────────────
function updateCount(listId, countId) {
    const count = document.querySelectorAll(`#${listId} .dir-item:not(.item-inactive)`).length;
    const el = document.getElementById(countId);
    if (el) el.textContent = count + ' ta';
}

// ── CONFIRM ───────────────────────────────────────────────────────────────────
let _confirmCb = null;

function confirm(msg, onOk) {
    document.getElementById('confirmMsg').textContent = msg;
    _confirmCb = onOk;
    openModal('confirmModal');
}

document.getElementById('confirmOk')?.addEventListener('click', () => {
    closeModal('confirmModal');
    if (_confirmCb) { _confirmCb(); _confirmCb = null; }
});

// ═══════════════════════════ CATEGORIES ═══════════════════════════════════════

// Build category item HTML
function buildCatItem(cat) {
    return `
    <div class="dir-item" id="cat-${cat.id}"
         data-id="${cat.id}" data-name="${cat.name}">
        <div class="di-bullet cat-bullet"></div>
        <div class="di-body">
            <span class="di-name">${cat.name}</span>
        </div>
        <div class="di-actions">
            <button class="dia-btn edit-cat"
                    data-id="${cat.id}" data-name="${cat.name}"
                    title="Tahrirlash">
                <i class="fa fa-pen"></i>
            </button>
            <button class="dia-btn delete-cat"
                    data-id="${cat.id}" data-name="${cat.name}"
                    title="O'chirish">
                <i class="fa fa-trash"></i>
            </button>
        </div>
    </div>`;
}

// Open add modal
document.getElementById('openAddCat')?.addEventListener('click', () => {
    document.getElementById('catModalTitle').textContent = "Kategoriya qo'shish";
    document.getElementById('catId').value   = '';
    document.getElementById('catName').value = '';
    clearErr('catErr');
    openModal('catModal');
    setTimeout(() => document.getElementById('catName')?.focus(), 100);
});

// Open edit modal (event delegation)
document.getElementById('catList')?.addEventListener('click', e => {
    // Edit
    const editBtn = e.target.closest('.edit-cat');
    if (editBtn) {
        document.getElementById('catModalTitle').textContent = 'Kategoriyani tahrirlash';
        document.getElementById('catId').value   = editBtn.dataset.id;
        document.getElementById('catName').value = editBtn.dataset.name;
        clearErr('catErr');
        openModal('catModal');
        setTimeout(() => document.getElementById('catName')?.focus(), 100);
        return;
    }

    // Delete
    const delBtn = e.target.closest('.delete-cat');
    if (delBtn) {
        confirm(
            `"${delBtn.dataset.name}" kategoriyasini o'chirishni tasdiqlaysizmi?`,
            () => deleteCat(delBtn.dataset.id, delBtn.dataset.name)
        );
    }
});

// Save (add/edit)
document.getElementById('catForm')?.addEventListener('submit', async e => {
    e.preventDefault();
    clearErr('catErr');

    const form = e.target;
    const btn  = document.getElementById('catSubmit');
    btn.disabled = true;

    try {
        const resp = await fetch(window.DIR_URLS.catSave, {
            method: 'POST',
            body:   new FormData(form),
            headers: { 'X-CSRFToken': csrf(), 'X-Requested-With': 'XMLHttpRequest' }
        });
        const data = await resp.json();

        if (data.status === 'success') {
            const isEdit = !!document.getElementById('catId').value;
            closeModal('catModal');

            if (isEdit) {
                // Update existing card
                const card = document.getElementById(`cat-${data.id}`);
                if (card) {
                    card.dataset.name = data.name;
                    const nameEl = card.querySelector('.di-name');
                    if (nameEl) nameEl.textContent = data.name;
                    // update data attrs on buttons
                    card.querySelectorAll('[data-id]').forEach(btn => {
                        btn.dataset.name = data.name;
                    });
                }
                toast('Kategoriya yangilandi!');
            } else {
                // Add new card
                const list  = document.getElementById('catList');
                const empty = list?.querySelector('.dir-empty');
                if (empty) empty.remove();
                list?.insertAdjacentHTML('beforeend', buildCatItem(data));
                updateCount('catList', 'catCount');
                toast('Kategoriya qo\'shildi!');
            }
        } else {
            showErr('catErr', data.errors || data.message || 'Xatolik');
        }
    } catch (err) {
        console.error(err);
        showErr('catErr', 'Server bilan xatolik');
    } finally {
        btn.disabled = false;
    }
});

// Delete category
async function deleteCat(id, name) {
    try {
        const url  = window.DIR_URLS.catDelete.replace('/0/', `/${id}/`);
        const resp = await fetch(url, {
            method: 'POST',
            body:   new URLSearchParams({ csrfmiddlewaretoken: csrf() }),
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        });
        const data = await resp.json();

        if (data.status === 'success') {
            const card = document.getElementById(`cat-${id}`);
            if (card) {
                card.classList.add('item-inactive');
                // Remove delete button
                card.querySelector('.delete-cat')?.remove();
                // Add inactive tag
                const body = card.querySelector('.di-body');
                if (body && !body.querySelector('.di-tag')) {
                    body.insertAdjacentHTML(
                        'beforeend',
                        '<span class="di-tag inactive">O\'chirilgan</span>'
                    );
                }
            }
            updateCount('catList', 'catCount');
            toast(`"${name}" o'chirildi`);
        } else {
            toast(data.message || 'Xatolik yuz berdi', 'error');
        }
    } catch (err) {
        console.error(err);
        toast('Server bilan xatolik', 'error');
    }
}

// ═══════════════════════════ REGIONS ══════════════════════════════════════════

// Build region item HTML
function buildRegItem(reg) {
    const orderHtml = reg.order
        ? `<span class="di-order"><i class="fa fa-sort"></i> ${reg.order}</span>`
        : '';
    return `
    <div class="dir-item" id="reg-${reg.id}"
         data-id="${reg.id}" data-name="${reg.name}" data-order="${reg.order || 0}">
        <div class="di-bullet reg-bullet"></div>
        <div class="di-body">
            <span class="di-name">${reg.name}</span>
            ${orderHtml}
        </div>
        <div class="di-actions">
            <button class="dia-btn edit-reg"
                    data-id="${reg.id}"
                    data-name="${reg.name}"
                    data-order="${reg.order || 0}"
                    title="Tahrirlash">
                <i class="fa fa-pen"></i>
            </button>
            <button class="dia-btn delete-reg"
                    data-id="${reg.id}"
                    data-name="${reg.name}"
                    title="O'chirish">
                <i class="fa fa-trash"></i>
            </button>
        </div>
    </div>`;
}

// Open add modal
document.getElementById('openAddReg')?.addEventListener('click', () => {
    document.getElementById('regModalTitle').textContent = "Viloyat qo'shish";
    document.getElementById('regId').value    = '';
    document.getElementById('regName').value  = '';
    document.getElementById('regOrder').value = '';
    clearErr('regErr');

    // Region modal field focus color fix
    document.getElementById('regName').style.setProperty('--focus-color', 'var(--reg)');

    openModal('regModal');
    setTimeout(() => document.getElementById('regName')?.focus(), 100);
});

// Open edit (event delegation)
document.getElementById('regList')?.addEventListener('click', e => {
    // Edit
    const editBtn = e.target.closest('.edit-reg');
    if (editBtn) {
        document.getElementById('regModalTitle').textContent = 'Viloyatni tahrirlash';
        document.getElementById('regId').value    = editBtn.dataset.id;
        document.getElementById('regName').value  = editBtn.dataset.name;
        document.getElementById('regOrder').value = editBtn.dataset.order || '';
        clearErr('regErr');
        openModal('regModal');
        setTimeout(() => document.getElementById('regName')?.focus(), 100);
        return;
    }

    // Delete
    const delBtn = e.target.closest('.delete-reg');
    if (delBtn) {
        confirm(
            `"${delBtn.dataset.name}" viloyatini o'chirishni tasdiqlaysizmi?`,
            () => deleteReg(delBtn.dataset.id, delBtn.dataset.name)
        );
    }
});

// Save region
document.getElementById('regForm')?.addEventListener('submit', async e => {
    e.preventDefault();
    clearErr('regErr');

    const form = e.target;
    const btn  = document.getElementById('regSubmit');
    btn.disabled = true;

    try {
        const resp = await fetch(window.DIR_URLS.regSave, {
            method: 'POST',
            body:   new FormData(form),
            headers: { 'X-CSRFToken': csrf(), 'X-Requested-With': 'XMLHttpRequest' }
        });
        const data = await resp.json();

        if (data.status === 'success') {
            const isEdit = !!document.getElementById('regId').value;
            closeModal('regModal');

            if (isEdit) {
                const card = document.getElementById(`reg-${data.id}`);
                if (card) {
                    card.dataset.name  = data.name;
                    card.dataset.order = data.order || 0;

                    const nameEl = card.querySelector('.di-name');
                    if (nameEl) nameEl.textContent = data.name;

                    const orderEl = card.querySelector('.di-order');
                    if (data.order) {
                        if (orderEl) {
                            orderEl.innerHTML = `<i class="fa fa-sort"></i> ${data.order}`;
                        } else {
                            card.querySelector('.di-body')?.insertAdjacentHTML(
                                'beforeend',
                                `<span class="di-order"><i class="fa fa-sort"></i> ${data.order}</span>`
                            );
                        }
                    } else if (orderEl) {
                        orderEl.remove();
                    }

                    card.querySelectorAll('[data-id]').forEach(b => {
                        b.dataset.name  = data.name;
                        b.dataset.order = data.order || 0;
                    });
                }
                toast('Viloyat yangilandi!');
            } else {
                const list  = document.getElementById('regList');
                const empty = list?.querySelector('.dir-empty');
                if (empty) empty.remove();
                list?.insertAdjacentHTML('beforeend', buildRegItem(data));
                updateCount('regList', 'regCount');
                toast('Viloyat qo\'shildi!');
            }
        } else {
            showErr('regErr', data.errors || data.message || 'Xatolik');
        }
    } catch (err) {
        console.error(err);
        showErr('regErr', 'Server bilan xatolik');
    } finally {
        btn.disabled = false;
    }
});

// Delete region
async function deleteReg(id, name) {
    try {
        const url  = window.DIR_URLS.regDelete.replace('/0/', `/${id}/`);
        const resp = await fetch(url, {
            method: 'POST',
            body:   new URLSearchParams({ csrfmiddlewaretoken: csrf() }),
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        });
        const data = await resp.json();

        if (data.status === 'success') {
            const card = document.getElementById(`reg-${id}`);
            if (card) {
                card.classList.add('item-inactive');
                card.querySelector('.delete-reg')?.remove();
                const body = card.querySelector('.di-body');
                if (body && !body.querySelector('.di-tag')) {
                    body.insertAdjacentHTML(
                        'beforeend',
                        '<span class="di-tag inactive">O\'chirilgan</span>'
                    );
                }
            }
            updateCount('regList', 'regCount');
            toast(`"${name}" o'chirildi`);
        } else {
            toast(data.message || 'Xatolik', 'error');
        }
    } catch (err) {
        console.error(err);
        toast('Server bilan xatolik', 'error');
    }
}

// ── Region modal input focus color ────────────────────────────────────────────
// Override cat focus color for region fields
const regFields = document.querySelectorAll('#regModal .field-in');
regFields.forEach(f => {
    f.addEventListener('focus', () => {
        f.style.borderColor = 'var(--reg)';
        f.style.boxShadow   = '0 0 0 3px var(--reg-d)';
    });
    f.addEventListener('blur', () => {
        f.style.borderColor = '';
        f.style.boxShadow   = '';
    });
});