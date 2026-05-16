/* ═══════════════════════════════════════════════════════════════
   settings.js  —  Sozlamalar (profil + parol)
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

// ── FEEDBACK (form ichidagi xabar) ────────────────────────────────────────────
function showFeedback(elId, msg, type = 'success') {
    const el = document.getElementById(elId);
    if (!el) return;
    el.textContent  = '';
    el.className    = `form-feedback ${type}`;
    el.classList.remove('d-none');

    if (typeof msg === 'object') {
        // Django form.errors
        Object.entries(msg).forEach(([field, msgs]) => {
            const line = document.createElement('div');
            const label = field === '__all__' ? '' : `${field}: `;
            line.textContent = label + (Array.isArray(msgs) ? msgs.join(', ') : msgs);
            el.appendChild(line);
        });
    } else {
        el.textContent = msg;
    }
}

function clearFeedback(elId) {
    const el = document.getElementById(elId);
    if (!el) return;
    el.textContent = '';
    el.classList.add('d-none');
}

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

// ══════════════════════════════════════════════════════════════════════════════
//  PROFILE FORM
// ══════════════════════════════════════════════════════════════════════════════
const profileForm = document.getElementById('profileForm');

profileForm?.addEventListener('submit', async e => {
    e.preventDefault();
    clearFeedback('profileFeedback');

    const btn     = profileForm.querySelector('[type=submit]');
    const origTxt = btn.innerHTML;
    btn.disabled  = true;
    btn.innerHTML = '<i class="fa fa-spinner fa-spin"></i> Saqlanmoqda...';

    try {
        const res  = await fetch(window.SETTINGS_URL, {
            method:  'POST',
            headers: { 'X-CSRFToken': getCsrf() },
            body:    new FormData(profileForm),
        });
        const data = await res.json();

        if (data.status === 'success') {
            showFeedback('profileFeedback', data.message || 'Profil yangilandi!', 'success');
            showToast('✅ Profil yangilandi!');

            // Header / avatar yangilash
            if (data.username) {
                updateProfileDisplay(data.username);
            }
        } else {
            showFeedback('profileFeedback', data.errors || data.message || 'Xatolik yuz berdi', 'error');
        }
    } catch {
        showFeedback('profileFeedback', 'Server bilan bog\'lanishda xatolik', 'error');
    } finally {
        btn.disabled  = false;
        btn.innerHTML = origTxt;
    }
});

// ── Avatar va ism yangilash ───────────────────────────────────────────────────
function updateProfileDisplay(username) {
    // Avatar initials
    const avatar = document.querySelector('.profile-avatar');
    if (avatar) avatar.textContent = username.slice(0, 2).toUpperCase();

    // Profile name
    const nameEl = document.querySelector('.profile-name');
    if (nameEl) nameEl.textContent = username;

    // Username input qiymatini ham yangilash (agar boshqa tab ochilsa)
    const usernameInput = profileForm?.querySelector('[name=username]');
    if (usernameInput) usernameInput.value = username;
}

// ══════════════════════════════════════════════════════════════════════════════
//  PASSWORD FORM
// ══════════════════════════════════════════════════════════════════════════════
const passwordForm  = document.getElementById('passwordForm');
const newPassInput  = document.getElementById('newPass');
const confirmInput  = document.getElementById('confirmPass');
const oldPassInput  = document.getElementById('oldPass');
const passSubmitBtn = document.getElementById('passSubmitBtn');
const psBar         = document.getElementById('psBar');
const psLabel       = document.getElementById('psLabel');
const matchHint     = document.getElementById('matchHint');

// ── Parol kuchi hisoblash ─────────────────────────────────────────────────────
function calcStrength(pass) {
    if (!pass) return 0;
    let score = 0;
    if (pass.length >= 6)  score++;
    if (pass.length >= 10) score++;
    if (/[A-Z]/.test(pass)) score++;
    if (/[0-9]/.test(pass)) score++;
    if (/[^A-Za-z0-9]/.test(pass)) score++;
    return score; // 0–5
}

const STRENGTH_MAP = [
    { label: '',           color: '',          width: '0%'   },
    { label: 'Juda zaif',  color: '#ef4444',   width: '20%'  },
    { label: 'Zaif',       color: '#f97316',   width: '40%'  },
    { label: "O'rtacha",   color: '#eab308',   width: '60%'  },
    { label: 'Kuchli',     color: '#22c55e',   width: '80%'  },
    { label: 'Juda kuchli',color: '#16a34a',   width: '100%' },
];

newPassInput?.addEventListener('input', () => {
    const val    = newPassInput.value;
    const score  = calcStrength(val);
    const entry  = STRENGTH_MAP[score];

    if (psBar) {
        psBar.style.width            = val ? entry.width : '0%';
        psBar.style.backgroundColor  = entry.color;
        psBar.style.transition       = 'width 0.3s ease, background-color 0.3s ease';
    }
    if (psLabel) {
        psLabel.textContent = val ? entry.label : '';
        psLabel.style.color = entry.color;
    }

    checkMatch();
    toggleSubmitBtn();
});

// ── Parol mos kelishi tekshiruvi ──────────────────────────────────────────────
function checkMatch() {
    if (!matchHint) return;

    const newVal  = newPassInput?.value  || '';
    const confVal = confirmInput?.value  || '';

    if (!confVal) {
        matchHint.classList.add('d-none');
        return;
    }

    matchHint.classList.remove('d-none');

    if (newVal === confVal) {
        matchHint.textContent = '✓ Parollar mos keldi';
        matchHint.style.color = '#22c55e';
    } else {
        matchHint.textContent = '✗ Parollar mos emas';
        matchHint.style.color = '#ef4444';
    }
}

confirmInput?.addEventListener('input', () => {
    checkMatch();
    toggleSubmitBtn();
});

oldPassInput?.addEventListener('input', toggleSubmitBtn);

// ── Submit tugmasini faollashtirish ───────────────────────────────────────────
function toggleSubmitBtn() {
    if (!passSubmitBtn) return;

    const oldVal  = oldPassInput?.value.trim()  || '';
    const newVal  = newPassInput?.value          || '';
    const confVal = confirmInput?.value          || '';
    const matches = newVal === confVal;
    const strong  = newVal.length >= 6;

    passSubmitBtn.disabled = !(oldVal && strong && matches);
}

// ── Password form submit ──────────────────────────────────────────────────────
passwordForm?.addEventListener('submit', async e => {
    e.preventDefault();
    clearFeedback('passwordFeedback');

    const newVal  = newPassInput?.value  || '';
    const confVal = confirmInput?.value  || '';

    // Client-side tekshirish
    if (newVal !== confVal) {
        showFeedback('passwordFeedback', 'Yangi parollar mos emas!', 'error');
        return;
    }
    if (newVal.length < 6) {
        showFeedback('passwordFeedback', 'Parol kamida 6 ta belgi bo\'lishi kerak!', 'error');
        return;
    }

    const btn     = passSubmitBtn;
    const origTxt = btn.innerHTML;
    btn.disabled  = true;
    btn.innerHTML = '<i class="fa fa-spinner fa-spin"></i> O\'zgartirilmoqda...';

    try {
        const res  = await fetch(window.SETTINGS_URL, {
            method:  'POST',
            headers: { 'X-CSRFToken': getCsrf() },
            body:    new FormData(passwordForm),
        });
        const data = await res.json();

        if (data.status === 'success') {
            showFeedback('passwordFeedback', data.message || 'Parol muvaffaqiyatli o\'zgartirildi!', 'success');
            showToast('🔒 Parol o\'zgartirildi!');
            passwordForm.reset();

            // Strength bar reset
            if (psBar)   { psBar.style.width = '0%'; psBar.style.backgroundColor = ''; }
            if (psLabel) psLabel.textContent = '';
            if (matchHint) matchHint.classList.add('d-none');

            passSubmitBtn.disabled = true;
        } else {
            showFeedback('passwordFeedback', data.errors || data.message || 'Xatolik yuz berdi', 'error');
        }
    } catch {
        showFeedback('passwordFeedback', 'Server bilan bog\'lanishda xatolik', 'error');
    } finally {
        btn.disabled  = false;
        btn.innerHTML = origTxt;
    }
});