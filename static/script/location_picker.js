/**
 * location_picker.js
 * ──────────────────────────────────────────────────────────────────────────
 * NoteBook — Manzil tanlash moduli
 * Leaflet.js + OpenStreetMap (100% bepul, API key shart emas)
 *
 * Imkoniyatlar:
 *   1. Xaritada pin qo'yish → lat/lng forma maydonlariga yoziladi
 *   2. Manzil yozib qidirish (Nominatim geocoding — bepul)
 *   3. "Mening joylashuvim" tugmasi
 *   4. client_detail.html da embed mini xarita
 *   5. Mavjud koordinatani edit modal da ko'rsatish
 *
 * CDN (base.html yoki client.html <head> ga bir marta qo'shish):
 *   <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
 *   <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
 * ──────────────────────────────────────────────────────────────────────────
 */

const LocationPicker = (() => {

  let pickerMap    = null;
  let pickerMarker = null;
  let viewerMap    = null;

  const DEFAULT_LAT = 41.2995;  // Toshkent
  const DEFAULT_LNG = 69.2401;

  function isLeafletLoaded() {
    return typeof L !== 'undefined';
  }

  // ── Leaflet + CSS dinamik yuklash ─────────────────────────────────────────
  function loadLeaflet() {
    return new Promise((resolve, reject) => {
      if (isLeafletLoaded()) { resolve(); return; }

      if (!document.querySelector('link[href*="leaflet"]')) {
        const css  = document.createElement('link');
        css.rel    = 'stylesheet';
        css.href   = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
        document.head.appendChild(css);
      }

      const script    = document.createElement('script');
      script.src      = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
      script.onload   = resolve;
      script.onerror  = () => reject(new Error('Leaflet yuklanmadi'));
      document.head.appendChild(script);
    });
  }

  // ── Nominatim: manzil → koordinata (bepul) ────────────────────────────────
  async function geocodeAddress(query) {
    const url  = `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(query)}&format=json&limit=1&countrycodes=uz`;
    const resp = await fetch(url, {
      headers: { 'Accept-Language': 'uz,ru', 'User-Agent': 'NoteBook-App' }
    });
    const data = await resp.json();
    if (!data.length) throw new Error('Manzil topilmadi');
    return { lat: parseFloat(data[0].lat), lng: parseFloat(data[0].lon), display: data[0].display_name };
  }

  // ── Nominatim: koordinata → manzil (bepul) ────────────────────────────────
  async function reverseGeocode(lat, lng) {
    try {
      const url  = `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lng}&format=json`;
      const resp = await fetch(url, { headers: { 'Accept-Language': 'uz,ru', 'User-Agent': 'NoteBook-App' } });
      const data = await resp.json();
      return data.display_name || `${lat.toFixed(5)}, ${lng.toFixed(5)}`;
    } catch {
      return `${lat.toFixed(5)}, ${lng.toFixed(5)}`;
    }
  }

  // ── Modal HTML ────────────────────────────────────────────────────────────
  function buildModalHtml() {
    return `
      <div class="modal fade" id="locationPickerModal" tabindex="-1" data-bs-backdrop="static">
        <div class="modal-dialog modal-lg">
          <div class="modal-content">
            <div class="modal-header py-2">
              <h6 class="modal-title">
                <i class="fa fa-map-marker-alt text-danger me-2"></i>Manzilni xaritada belgilang
              </h6>
              <button type="button" class="btn-close btn-close-sm" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body p-0">

              <div class="p-3 border-bottom bg-light d-flex gap-2">
                <input type="text" id="locationSearchInput" class="form-control form-control-sm"
                       placeholder="Manzil yozing (masalan: Chilonzor, Toshkent)..."
                       onkeydown="if(event.key==='Enter'){event.preventDefault();LocationPicker.searchAddress();}">
                <button class="btn btn-sm btn-outline-primary" id="locationSearchBtn"
                        onclick="LocationPicker.searchAddress()" title="Qidirish">
                  <i class="fa fa-search"></i>
                </button>
                <button class="btn btn-sm btn-outline-secondary"
                        onclick="LocationPicker.useMyLocation()" title="Mening joylashuvim">
                  <i class="fa fa-location-crosshairs"></i>
                </button>
              </div>

              <div id="locationPickerMap" style="height:420px; width:100%; z-index:1;"></div>

              <div class="p-3 border-top bg-light">
                <div class="row g-2 align-items-center">
                  <div class="col-md-5">
                    <div class="input-group input-group-sm">
                      <span class="input-group-text text-muted">Lat</span>
                      <input type="text" id="pickerLatDisplay" class="form-control" readonly
                             placeholder="Xaritaga bosing...">
                    </div>
                  </div>
                  <div class="col-md-5">
                    <div class="input-group input-group-sm">
                      <span class="input-group-text text-muted">Lng</span>
                      <input type="text" id="pickerLngDisplay" class="form-control" readonly
                             placeholder="Xaritaga bosing...">
                    </div>
                  </div>
                  <div class="col-md-2">
                    <button class="btn btn-sm btn-outline-danger w-100"
                            onclick="LocationPicker.clearPin()">
                      <i class="fa fa-trash"></i>
                    </button>
                  </div>
                </div>
                <div id="pickerAddressDisplay" class="text-muted mt-2" style="font-size:0.82rem;">
                  <i class="fa fa-info-circle me-1"></i>Xaritaning istalgan joyiga bosib pin qo'ying
                </div>
              </div>

            </div>
            <div class="modal-footer py-2">
              <small class="text-muted me-auto" style="font-size:0.75rem;">
                © <a href="https://www.openstreetmap.org/copyright" target="_blank"
                     class="text-muted">OpenStreetMap</a> contributors
              </small>
              <button class="btn btn-sm btn-secondary" data-bs-dismiss="modal">Bekor</button>
              <button class="btn btn-sm btn-primary" id="locationPickerSaveBtn" disabled
                      onclick="LocationPicker.savePin()">
                <i class="fa fa-check me-1"></i>Saqlash
              </button>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  // ── Picker modalini ochish (public) ───────────────────────────────────────
  async function openPicker(options = {}) {
    const { currentLat = null, currentLng = null, onSelect = null } = options;

    document.getElementById('locationPickerModal')?.remove();
    document.body.insertAdjacentHTML('beforeend', buildModalHtml());

    const modalEl = document.getElementById('locationPickerModal');
    const modal   = new bootstrap.Modal(modalEl);
    modal.show();

    modalEl.addEventListener('shown.bs.modal', async () => {
      try {
        await loadLeaflet();
        initPickerMap(currentLat, currentLng, onSelect);
      } catch (err) {
        document.getElementById('locationPickerMap').innerHTML = `
          <div class="d-flex align-items-center justify-content-center h-100 p-4 text-danger">
            <div class="text-center">
              <i class="fa fa-exclamation-triangle fs-1 d-block mb-2"></i>
              <p class="mb-0">Xarita yuklanmadi: ${err.message}</p>
              <small class="text-muted">Internet aloqasini tekshiring</small>
            </div>
          </div>
        `;
      }
    }, { once: true });

    modalEl.addEventListener('hidden.bs.modal', () => {
      if (pickerMap) { pickerMap.remove(); pickerMap = null; }
      pickerMarker = null;
      modalEl.remove();
    }, { once: true });
  }

  // ── Xaritani initialize qilish ────────────────────────────────────────────
  function initPickerMap(currentLat, currentLng, onSelectCallback) {
    const lat  = currentLat ? parseFloat(currentLat) : DEFAULT_LAT;
    const lng  = currentLng ? parseFloat(currentLng) : DEFAULT_LNG;
    const zoom = currentLat ? 15 : 12;

    pickerMap = L.map('locationPickerMap').setView([lat, lng], zoom);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      maxZoom: 19,
    }).addTo(pickerMap);

    // Mavjud koordinata bo'lsa pin ko'rsatish
    if (currentLat && currentLng) {
      setPin(lat, lng, false);
      updateDisplayFields(lat, lng);
      reverseGeocode(lat, lng).then(addr => {
        const el = document.getElementById('pickerAddressDisplay');
        if (el) el.innerHTML = `<i class="fa fa-map-marker-alt me-1"></i>${addr}`;
      });
    }

    // Xaritaga bosishda pin
    pickerMap.on('click', async (e) => {
      const { lat: cLat, lng: cLng } = e.latlng;
      setPin(cLat, cLng, true);
      updateDisplayFields(cLat, cLng);
      const el = document.getElementById('pickerAddressDisplay');
      if (el) el.innerHTML = `<i class="fa fa-spinner fa-spin me-1"></i>Manzil aniqlanmoqda...`;
      const addr = await reverseGeocode(cLat, cLng);
      if (el) el.innerHTML = `<i class="fa fa-map-marker-alt me-1"></i>${addr}`;
    });

    pickerMap._onSelect = onSelectCallback;
  }

  // ── Pin qo'yish / ko'chirish ──────────────────────────────────────────────
  function setPin(lat, lng, animate = true) {
    if (pickerMarker) {
      pickerMarker.setLatLng([lat, lng]);
    } else {
      pickerMarker = L.marker([lat, lng], { draggable: true }).addTo(pickerMap);

      pickerMarker.on('dragend', async () => {
        const pos  = pickerMarker.getLatLng();
        updateDisplayFields(pos.lat, pos.lng);
        const el   = document.getElementById('pickerAddressDisplay');
        if (el) el.innerHTML = `<i class="fa fa-spinner fa-spin me-1"></i>Manzil aniqlanmoqda...`;
        const addr = await reverseGeocode(pos.lat, pos.lng);
        if (el) el.innerHTML = `<i class="fa fa-map-marker-alt me-1"></i>${addr}`;
      });
    }

    const saveBtn = document.getElementById('locationPickerSaveBtn');
    if (saveBtn) saveBtn.disabled = false;

    // Kichik bounce animatsiya
    if (animate) {
      const icon = pickerMarker.getElement();
      if (icon) {
        icon.style.transition = 'transform 0.15s ease';
        icon.style.transform  = 'scale(1.4)';
        setTimeout(() => { icon.style.transform = 'scale(1)'; }, 150);
      }
    }
  }

  // ── Koordinatalarni ko'rsatish ────────────────────────────────────────────
  function updateDisplayFields(lat, lng) {
    const latEl = document.getElementById('pickerLatDisplay');
    const lngEl = document.getElementById('pickerLngDisplay');
    if (latEl) latEl.value = lat.toFixed(6);
    if (lngEl) lngEl.value = lng.toFixed(6);
  }

  // ── Manzil qidirish ───────────────────────────────────────────────────────
  async function searchAddress() {
    const input = document.getElementById('locationSearchInput');
    const btn   = document.getElementById('locationSearchBtn');
    const query = input?.value.trim();
    if (!query || !pickerMap) return;

    if (btn) btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';

    try {
      const result = await geocodeAddress(query);
      pickerMap.setView([result.lat, result.lng], 16);
      setPin(result.lat, result.lng, true);
      updateDisplayFields(result.lat, result.lng);
      const el = document.getElementById('pickerAddressDisplay');
      if (el) el.innerHTML = `<i class="fa fa-map-marker-alt me-1"></i>${result.display}`;
    } catch {
      showToast("Manzil topilmadi. Aniqroq yozing (masalan: Yunusobod tumani, Toshkent)", 'warning');
    } finally {
      if (btn) btn.innerHTML = '<i class="fa fa-search"></i>';
    }
  }

  // ── Mening joylashuvim ────────────────────────────────────────────────────
  function useMyLocation() {
    if (!navigator.geolocation) {
      showToast("Brauzer geolocation ni qo'llab-quvvatlamaydi", 'warning');
      return;
    }
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const lat = pos.coords.latitude;
        const lng = pos.coords.longitude;
        if (!pickerMap) return;
        pickerMap.setView([lat, lng], 16);
        setPin(lat, lng, true);
        updateDisplayFields(lat, lng);
        const addr = await reverseGeocode(lat, lng);
        const el   = document.getElementById('pickerAddressDisplay');
        if (el) el.innerHTML = `<i class="fa fa-location-crosshairs me-1"></i>${addr}`;
      },
      () => showToast("Joylashuvni aniqlashda xatolik. Ruxsat bering.", 'warning')
    );
  }

  // ── Pinni o'chirish ───────────────────────────────────────────────────────
  function clearPin() {
    if (pickerMarker) { pickerMarker.remove(); pickerMarker = null; }
    const latEl   = document.getElementById('pickerLatDisplay');
    const lngEl   = document.getElementById('pickerLngDisplay');
    const addrEl  = document.getElementById('pickerAddressDisplay');
    const saveBtn = document.getElementById('locationPickerSaveBtn');
    if (latEl)   latEl.value   = '';
    if (lngEl)   lngEl.value   = '';
    if (addrEl)  addrEl.innerHTML = '<i class="fa fa-info-circle me-1"></i>Pin o\'chirildi';
    if (saveBtn) saveBtn.disabled = true;
  }

  // ── Saqlash (callbackga yuborish) ─────────────────────────────────────────
  async function savePin() {
    const lat = parseFloat(document.getElementById('pickerLatDisplay')?.value);
    const lng = parseFloat(document.getElementById('pickerLngDisplay')?.value);
    if (isNaN(lat) || isNaN(lng)) return;

    const addrEl  = document.getElementById('pickerAddressDisplay');
    const address = addrEl ? addrEl.textContent.replace(/^[^\w]*/, '').trim() : '';

    if (pickerMap?._onSelect) {
      pickerMap._onSelect(lat, lng, address);
    }

    bootstrap.Modal.getInstance(document.getElementById('locationPickerModal'))?.hide();
  }

  // ── Mini embed xarita (client_detail uchun) ───────────────────────────────
  async function initViewerMap(containerId, lat, lng, label = '') {
    const container = document.getElementById(containerId);
    if (!container) return;

    try {
      await loadLeaflet();
      await new Promise(r => setTimeout(r, 50));

      viewerMap = L.map(containerId, {
        zoomControl:     true,
        scrollWheelZoom: false,
        dragging:        true,
      }).setView([parseFloat(lat), parseFloat(lng)], 15);

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
        maxZoom: 19,
      }).addTo(viewerMap);

      const marker = L.marker([parseFloat(lat), parseFloat(lng)]).addTo(viewerMap);
      if (label) marker.bindPopup(`<strong>${label}</strong>`).openPopup();

      setTimeout(() => viewerMap.invalidateSize(), 200);

    } catch {
      if (container) container.innerHTML = `
        <div class="d-flex align-items-center justify-content-center h-100 bg-light rounded text-muted">
          <div class="text-center p-3">
            <i class="fa fa-map fs-2 mb-2 d-block"></i>
            <small>Xarita yuklanmadi</small>
          </div>
        </div>
      `;
    }
  }

  // ── Toast ─────────────────────────────────────────────────────────────────
  function showToast(msg, type = 'info') {
    let container = document.getElementById('lpToastContainer');
    if (!container) {
      container = document.createElement('div');
      container.id = 'lpToastContainer';
      container.style.cssText = 'position:fixed;bottom:1rem;right:1rem;z-index:9999;';
      document.body.appendChild(container);
    }
    const id   = 'lpt_' + Date.now();
    const icon = { success:'✅', danger:'❌', warning:'⚠️', info:'ℹ️' }[type] || 'ℹ️';
    container.insertAdjacentHTML('beforeend', `
      <div id="${id}" class="toast align-items-center text-bg-${type} border-0 show mb-2">
        <div class="d-flex">
          <div class="toast-body">${icon} ${msg}</div>
          <button type="button" class="btn-close btn-close-white me-2 m-auto"
                  onclick="document.getElementById('${id}').remove()"></button>
        </div>
      </div>
    `);
    setTimeout(() => document.getElementById(id)?.remove(), 4000);
  }

  // ── Public API ────────────────────────────────────────────────────────────
  return { openPicker, initViewerMap, searchAddress, useMyLocation, clearPin, savePin };

})();