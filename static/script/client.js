'use strict';

class ClientManager {
    constructor() {
        this.searchInput   = document.getElementById('searchInput');
        this.searchClear   = document.getElementById('searchClear');
        this.clientList    = document.getElementById('clientList');
        this.totalCount    = document.getElementById('totalCount');
        this.statTotalDebt = document.getElementById('statTotalDebt');
        this.statAdvance   = document.getElementById('statTotalAdvance');
        this.statCount     = document.getElementById('statCount');
        this.totalContainers = document.getElementById('totalContainers');

        this.addModal    = document.getElementById('addClientModal');
        this.editModal   = document.getElementById('editClientModal');
        this.deleteModal = document.getElementById('deleteClientModal');

        this.currentRegion  = new URLSearchParams(window.location.search).get('region')  || '';
        this.currentSearch  = new URLSearchParams(window.location.search).get('search')  || '';
        this.currentBalance = new URLSearchParams(window.location.search).get('balance') || '';

        this.init();
    }

    init() {
        console.log('%c✅ ClientManager yuklandi', 'color:#00d4aa;font-weight:bold');
        this.bindEvents();
        this.bindLocationEvents();
        this.loadInitialStats();   // ← AJAX bilan umumiy grand total olish
        this.updateSearchClear();
    }

    // Sahifa birinchi yuklanganda grand total ni backend dan AJAX bilan olish
    async loadInitialStats() {
        try {
            const url = new URL(window.location.href);
            url.searchParams.delete('page');  // page parametri kerak emas
            const resp = await fetch(url.toString(), {
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });
            if (!resp.ok) { this.updateStatsFromDOM(); return; }
            const data = await resp.json();
            // Grand total keldi - to'g'ri ko'rsatamiz
            this.updateStats(
                data.clients || [],
                data.grand_total_debt    ?? null,
                data.grand_total_advance ?? null,
                data.grand_total_containers ?? null
            );
        } catch {
            // AJAX xato bo'lsa DOM dan hisoblash (fallback)
            this.updateStatsFromDOM();
        }
    }

    // ==================== DEBOUNCE ====================
    debounce(fn, delay = 380) {
        let t;
        return (...args) => { clearTimeout(t); t = setTimeout(() => fn.apply(this, args), delay); };
    }

    // ==================== CSRF ====================
    getCSRF() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    }

    // ==================== FORMAT ====================
    fmt(n) {
        return Math.round(n).toLocaleString('uz-UZ');
    }

    // ==================== STATS ====================
    updateStatsFromDOM() {
        const cards = this.clientList.querySelectorAll('.client-card');
        let totalDebt = 0, totalAdvance = 0, totalContainers = 0;
        cards.forEach(card => {
            totalDebt       += parseFloat(card.dataset.debt          || 0);
            totalAdvance    += parseFloat(card.dataset.advance       || 0);
            totalContainers += parseInt(card.dataset.containerTotal  || 0);
        });
        if (this.statTotalDebt)   this.statTotalDebt.textContent   = this.fmt(totalDebt)    + ' so\'m';
        if (this.statAdvance)     this.statAdvance.textContent     = this.fmt(totalAdvance) + ' so\'m';
        if (this.statCount)       this.statCount.textContent       = cards.length;
        if (this.totalContainers) this.totalContainers.textContent = totalContainers + ' ta';
    }

    updateStats(clients, grandTotalDebt = null, grandTotalAdvance = null, grandTotalContainers = null) {
        // Agar backend dan umumiy yig'indi kelgan bo'lsa — uni ishlatamiz
        // Aks holda joriy sahifadagi clientlar bo'yicha hisoblaymiz (fallback)
        const totalDebt       = grandTotalDebt       !== null ? grandTotalDebt       : clients.reduce((s, c) => s + (c.total_debt       || 0), 0);
        const totalAdvance    = grandTotalAdvance    !== null ? grandTotalAdvance    : clients.reduce((s, c) => s + (c.advance_balance  || 0), 0);
        const totalContainers = grandTotalContainers !== null ? grandTotalContainers : clients.reduce((s, c) => s + (c.container_total  || 0), 0);
        if (this.statTotalDebt)  this.statTotalDebt.textContent  = this.fmt(totalDebt)    + ' so\'m';
        if (this.statAdvance)    this.statAdvance.textContent    = this.fmt(totalAdvance) + ' so\'m';
        if (this.statCount)      this.statCount.textContent      = this.totalCount?.textContent || clients.length;
        if (this.totalContainers) this.totalContainers.textContent = totalContainers + ' ta';
    }

    // ==================== SEARCH CLEAR ====================
    updateSearchClear() {
        if (!this.searchClear) return;
        this.searchClear.style.display = this.searchInput?.value ? 'flex' : 'none';
    }

    // ==================== BUILD CLIENT CARD ====================
    buildCard(c) {
        const debt    = parseFloat(c.total_debt      || 0);
        const advance = parseFloat(c.advance_balance || 0);

        let badgeHtml, labelHtml;
        if (debt > 0) {
            badgeHtml = `<span class="balance-badge debt">-${this.fmt(debt)}</span>`;
            labelHtml = 'qarz';
        } else if (advance > 0) {
            badgeHtml = `<span class="balance-badge advance">+${this.fmt(advance)}</span>`;
            labelHtml = 'avans';
        } else {
            badgeHtml = `<span class="balance-badge zero">0</span>`;
            labelHtml = 'toza';
        }

        const regionTag = c.region_name
            ? `<span class="region-tag"><i class="fa fa-map-marker-alt"></i> ${c.region_name}</span>`
            : '';

        // Xaritada belgilangan bo'lsa badge ko'rsatish
        const mapTag = c.has_location
            ? `<span class="region-tag" style="color: var(--success-color, #28a745);">
                 <i class="fa fa-map-pin"></i> Xaritada
               </span>`
            : '';

        // Idishlar (container) badge — faqat 0 dan katta bo'lsa
        const containerTotal = parseInt(c.container_total || 0);
        const containerTag = containerTotal > 0
            ? `<span class="region-tag" style="color:#a855f7" title="Idishlar">
                 <i class="fa fa-box-open"></i> ${containerTotal} ta
               </span>`
            : '';

        const initial = (c.name || '?')[0].toUpperCase();

        return `
        <div class="client-card"
             data-id="${c.id}"
             data-name="${c.name || ''}"
             data-phone="${c.phone || ''}"
             data-address="${c.address || ''}"
             data-region-id="${c.region_id || ''}"
             data-debt="${debt}"
             data-advance="${advance}"
             data-lat="${c.latitude  || ''}"
             data-lng="${c.longitude || ''}"
             data-container-total="${containerTotal}">

            <div class="card-main" onclick="window.location.href='/clients/client/${c.id}/'">
                <div class="client-avatar">${initial}</div>
                <div class="client-info">
                    <div class="client-name">${c.name}</div>
                    <div class="client-meta">
                        <span><i class="fa fa-phone"></i> ${c.phone}</span>
                        ${regionTag}
                        ${mapTag}
                        ${containerTag}
                    </div>
                </div>
                <div class="client-balance">
                    ${badgeHtml}
                    <div class="balance-label">${labelHtml}</div>
                </div>
            </div>

            <div class="card-actions">
                <button class="ca-btn view-btn" data-id="${c.id}">
                    <i class="fa fa-eye"></i><span>Ko'rish</span>
                </button>
                ${(debt > 0 || advance > 0) ? `
                <a class="ca-btn sms-btn"
                   href="sms:${c.phone}?body=${encodeURIComponent(
                        debt > 0
                          ? `Assalomu alaykum, ${c.phone} raqami egasi! Sizning ${window.CURRENT_BUSINESS_NAME}dan ${this.fmt(debt)} so'm qarzingiz bor. Iltimos, tezroq to'lov qilib qo'ying!`
                          : `Assalomu alaykum, ${c.phone} raqami egasi! Sizning ${window.CURRENT_BUSINESS_NAME}da ${this.fmt(advance)} so'm avansingiz bor. Keyingi xaridingizda hisobga olinadi. Rahmat!`
                   )}"
                   onclick="event.stopPropagation()">
                    <i class="fa fa-comment-sms"></i><span>SMS</span>
                </a>
                <button class="ca-btn auto-sms-btn" data-id="${c.id}"
                        title="Avtomatik SMS yuborish (Eskiz.uz)"
                        onclick="event.stopPropagation()">
                    <i class="fa fa-paper-plane"></i><span>Avto SMS</span>
                </button>` : ''}
                <button class="ca-btn edit-btn"
                        data-id="${c.id}"
                        data-name="${c.name || ''}"
                        data-phone="${c.phone || ''}"
                        data-address="${c.address || ''}"
                        data-region-id="${c.region_id || ''}"
                        data-lat="${c.latitude  || ''}"
                        data-lng="${c.longitude || ''}">
                    <i class="fa fa-edit"></i><span>Tahrirlash</span>
                </button>
                <button class="ca-btn delete-btn"
                        data-id="${c.id}"
                        data-name="${c.name || ''}">
                    <i class="fa fa-unlink"></i><span>Aloqani uz</span>
                </button>
            </div>
        </div>`;
    }

    // ==================== LOAD CLIENTS (AJAX) ====================
    async loadClients(search = '', region = '', balance = '') {
        if (!this.clientList) return;

        this.clientList.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon" style="animation: pulse 1s infinite">
                    <i class="fa fa-spinner fa-spin"></i>
                </div>
            </div>`;

        try {
            const url = new URL(window.location.href);
            url.searchParams.set('search', search);
            url.searchParams.set('region', region);
            if (balance) {
                url.searchParams.set('balance', balance);
            } else {
                url.searchParams.delete('balance');
            }
            url.searchParams.delete('page');

            const resp = await fetch(url.toString(), {
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });
            if (!resp.ok) throw new Error(`${resp.status}`);
            const data = await resp.json();

            if (this.totalCount) {
                this.totalCount.textContent = data.total_count + ' ta';
            }

            if (!data.clients || data.clients.length === 0) {
                this.clientList.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-icon"><i class="fa fa-search"></i></div>
                        <h3>Hech narsa topilmadi</h3>
                        <p>Qidiruv shartlarini o'zgartiring</p>
                    </div>`;
                this.updateStats([]);
                return;
            }

            this.clientList.innerHTML = data.clients.map(c => this.buildCard(c)).join('');
            this.updateStats(data.clients, data.grand_total_debt ?? null, data.grand_total_advance ?? null, data.grand_total_containers ?? null);

        } catch (err) {
            console.error('loadClients error:', err);
            this.clientList.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon"><i class="fa fa-exclamation-triangle"></i></div>
                    <h3>Xatolik yuz berdi</h3>
                    <p>Sahifani yangilang</p>
                </div>`;
        }
    }

    // ==================== LOCATION EVENTS ====================
    bindLocationEvents() {

        // ── ADD modal — xarita tugmasi ───────────────────────────────────────
        document.getElementById('addMapBtn')?.addEventListener('click', () => {
            LocationPicker.openPicker({
                onSelect: (lat, lng, address) => {
                    document.getElementById('addLatInput').value = lat;
                    document.getElementById('addLngInput').value = lng;

                    // Agar address maydoni bo'sh bo'lsa — auto to'ldirish
                    const addrField = document.getElementById('addAddress');
                    if (addrField && !addrField.value.trim()) {
                        addrField.value = address;
                    }

                    // Preview
                    document.getElementById('addLocationPreviewText').textContent =
                        `${lat.toFixed(5)}, ${lng.toFixed(5)}`;
                    document.getElementById('addLocationPreview').style.display = 'block';
                }
            });
        });

        // ADD — preview o'chirish
        document.getElementById('addLocationClear')?.addEventListener('click', (e) => {
            e.preventDefault();
            document.getElementById('addLatInput').value  = '';
            document.getElementById('addLngInput').value  = '';
            document.getElementById('addLocationPreview').style.display = 'none';
        });

        // ADD modal — yopilganda tozalash
        this.addModal?.addEventListener('hidden.bs.modal', () => {
            document.getElementById('addLatInput').value  = '';
            document.getElementById('addLngInput').value  = '';
            document.getElementById('addLocationPreview').style.display = 'none';
        });

        // ── EDIT modal — xarita tugmasi ──────────────────────────────────────
        document.getElementById('editMapBtn')?.addEventListener('click', () => {
            const currentLat = document.getElementById('editLatInput').value  || null;
            const currentLng = document.getElementById('editLngInput').value  || null;

            LocationPicker.openPicker({
                currentLat,
                currentLng,
                onSelect: (lat, lng, address) => {
                    document.getElementById('editLatInput').value = lat;
                    document.getElementById('editLngInput').value = lng;

                    // Agar address bo'sh bo'lsa — auto to'ldirish
                    const addrField = document.getElementById('editAddress');
                    if (addrField && !addrField.value.trim()) {
                        addrField.value = address;
                    }

                    // Preview
                    document.getElementById('editLocationPreviewText').textContent =
                        `${lat.toFixed(5)}, ${lng.toFixed(5)}`;
                    document.getElementById('editLocationPreview').style.display = 'block';
                }
            });
        });

        // EDIT — preview o'chirish (koordinatani o'chiradi, addressni saqlab qoladi)
        document.getElementById('editLocationClear')?.addEventListener('click', (e) => {
            e.preventDefault();
            document.getElementById('editLatInput').value  = '';
            document.getElementById('editLngInput').value  = '';
            document.getElementById('editLocationPreview').style.display = 'none';
        });
    }

    // ==================== BIND EVENTS ====================
    bindEvents() {

        // Search input
        if (this.searchInput) {
            this.searchInput.addEventListener('input', this.debounce(() => {
                this.currentSearch = this.searchInput.value.trim();
                this.updateSearchClear();
                this.loadClients(this.currentSearch, this.currentRegion);
            }));
        }

        // Search clear
        if (this.searchClear) {
            this.searchClear.addEventListener('click', () => {
                this.searchInput.value = '';
                this.currentSearch = '';
                this.updateSearchClear();
                this.loadClients('', this.currentRegion, this.currentBalance);
                this.searchInput.focus();
            });
        }

        // Region filter chips
        document.querySelectorAll('#regionFilter .region-chip').forEach(chip => {
            chip.addEventListener('click', () => {
                document.querySelectorAll('#regionFilter .region-chip').forEach(c => c.classList.remove('active'));
                chip.classList.add('active');
                this.currentRegion = chip.dataset.region || '';
                this.loadClients(this.currentSearch, this.currentRegion, this.currentBalance);
            });
        });

        // Balance filter chips
        document.querySelectorAll('.balance-chip').forEach(chip => {
            chip.addEventListener('click', () => {
                document.querySelectorAll('.balance-chip').forEach(c => c.classList.remove('active'));
                chip.classList.add('active');
                this.currentBalance = chip.dataset.balance || '';
                this.loadClients(this.currentSearch, this.currentRegion, this.currentBalance);
            });
        });

        // Client list — event delegation
        if (this.clientList) {
            this.clientList.addEventListener('click', e => {
                const viewBtn    = e.target.closest('.view-btn');
                const editBtn    = e.target.closest('.edit-btn');
                const deleteBtn  = e.target.closest('.delete-btn');
                const autoSmsBtn = e.target.closest('.auto-sms-btn');

                if (viewBtn) {
                    window.location.href = `/clients/client/${viewBtn.dataset.id}/`;
                    return;
                }
                if (editBtn) {
                    this.openEditModal(editBtn.dataset);
                    return;
                }
                if (deleteBtn) {
                    this.openDeleteModal(deleteBtn.dataset);
                    return;
                }
                if (autoSmsBtn) {
                    this.sendAutoSms(autoSmsBtn);
                    return;
                }
            });
        }

        // Form submit handlers
        document.getElementById('addClientForm')?.addEventListener('submit',    e => this.handleAdd(e));
        document.getElementById('editClientForm')?.addEventListener('submit',   e => this.handleEdit(e));
        document.getElementById('deleteClientForm')?.addEventListener('submit', e => this.handleDelete(e));

        // Add modal — reset on open
        this.addModal?.addEventListener('show.bs.modal', () => {
            document.getElementById('addClientForm')?.reset();
        });
    }

    // ==================== AVTOMATIK SMS (Eskiz.uz) ====================
    async sendAutoSms(btn) {
        if (btn.disabled) return;
        const clientId   = btn.dataset.id;
        const originalHtml = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<i class="fa fa-spinner fa-spin"></i><span>Yuborilmoqda...</span>';

        try {
            const url  = window.SMS_SEND_URL.replace('0', clientId);
            const resp = await fetch(url, {
                method: 'POST',
                headers: { 'X-CSRFToken': this.getCSRF() },
            });
            const data = await resp.json();
            if (resp.ok && data.status === 'success') {
                btn.innerHTML = '<i class="fa fa-check"></i><span>Yuborildi</span>';
                setTimeout(() => { btn.innerHTML = originalHtml; btn.disabled = false; }, 2500);
            } else {
                alert(data.message || 'SMS yuborilmadi');
                btn.innerHTML = originalHtml;
                btn.disabled = false;
            }
        } catch {
            alert('Server bilan bog\'lanishda xatolik — SMS yuborilmadi');
            btn.innerHTML = originalHtml;
            btn.disabled = false;
        }
    }

    // ==================== MODAL HELPERS ====================
    openEditModal(data) {
        document.getElementById('editClientId').value  = data.id      || '';
        document.getElementById('editName').value      = data.name    || '';
        document.getElementById('editPhone').value     = data.phone   || '';
        document.getElementById('editAddress').value   = data.address || '';
        const regionSel = document.getElementById('editRegion');
        if (regionSel) regionSel.value = data.regionId || '';

        // ── Koordinatalarni yozish ────────────────────────────────────────────
        const lat = data.lat || '';
        const lng = data.lng || '';
        document.getElementById('editLatInput').value = lat;
        document.getElementById('editLngInput').value = lng;

        // Preview
        const preview     = document.getElementById('editLocationPreview');
        const previewText = document.getElementById('editLocationPreviewText');
        if (lat && lng) {
            previewText.textContent      = `${parseFloat(lat).toFixed(5)}, ${parseFloat(lng).toFixed(5)}`;
            preview.style.display        = 'block';
        } else {
            preview.style.display        = 'none';
        }

        new bootstrap.Modal(this.editModal).show();
    }

    openDeleteModal(data) {
        document.getElementById('deleteClientId').value        = data.id   || '';
        document.getElementById('deleteClientName').textContent = data.name || '';
        new bootstrap.Modal(this.deleteModal).show();
    }

    hideModal(modalEl) {
        const m = bootstrap.Modal.getInstance(modalEl);
        if (m) m.hide();
    }

    // ==================== FORM HANDLERS ====================
    async handleAdd(e) {
        e.preventDefault();
        const form = e.target;
        const btn  = form.querySelector('[type=submit]');
        btn.disabled = true;

        try {
            const resp = await fetch(form.action, {
                method: 'POST',
                body: new FormData(form),
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });
            const data = await resp.json();

            if (data.status === 'created') {
                this.hideModal(this.addModal);
                form.reset();
                // Koordinata preview ni ham tozalash
                document.getElementById('addLatInput').value  = '';
                document.getElementById('addLngInput').value  = '';
                document.getElementById('addLocationPreview').style.display = 'none';
                await this.loadClients(this.currentSearch, this.currentRegion, this.currentBalance);
            } else {
                alert(data.message || 'Xatolik yuz berdi');
            }
        } catch (err) {
            console.error(err);
            alert('Server bilan xatolik');
        } finally {
            btn.disabled = false;
        }
    }

    async handleEdit(e) {
        e.preventDefault();
        const form = e.target;
        const btn  = form.querySelector('[type=submit]');
        btn.disabled = true;

        try {
            const resp = await fetch(form.action, {
                method: 'POST',
                body: new FormData(form),
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });
            const data = await resp.json();

            if (data.status === 'updated') {
                this.hideModal(this.editModal);
                await this.loadClients(this.currentSearch, this.currentRegion, this.currentBalance);
            } else {
                alert(data.message || 'Xatolik yuz berdi');
            }
        } catch (err) {
            console.error(err);
            alert('Tahrirlashda xatolik');
        } finally {
            btn.disabled = false;
        }
    }

    async handleDelete(e) {
        e.preventDefault();
        const form = e.target;
        const btn  = form.querySelector('[type=submit]');
        btn.disabled = true;

        try {
            const resp = await fetch(form.action, {
                method: 'POST',
                body: new FormData(form),
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });
            const data = await resp.json();

            if (data.status === 'deleted') {
                this.hideModal(this.deleteModal);
                await this.loadClients(this.currentSearch, this.currentRegion, this.currentBalance);
            } else {
                alert(data.message || "O'chirishda xatolik");
            }
        } catch (err) {
            console.error(err);
            alert("O'chirishda xatolik yuz berdi");
        } finally {
            btn.disabled = false;
        }
    }
}

// ==================== INIT ====================
document.addEventListener('DOMContentLoaded', () => {
    new ClientManager();
});