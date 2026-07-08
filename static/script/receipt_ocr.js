/* ──────────────────────────────────────────────────────────────────────────
 * receipt_ocr.js — "Chekdan xarid" (OCR) moduli.
 *
 * O'zini o'zi o'rnatadi: modalni JS yaratadi, shuning uchun
 * branch_detail.html ga faqat TUGMA va shu skript qo'shiladi:
 *
 *   <button class="header-action-btn" id="openReceiptOcr" title="Chekdan xarid">
 *       <i class="fa fa-camera"></i>
 *   </button>
 *   <script src="{% static 'script/receipt_ocr.js' %}"
 *           data-branch-id="{{ branch.id }}"></script>
 *
 * Oqim: rasm tanlash/olish → /ocr/api/branch/<id>/scan/ → tahrirlanadigan
 * jadval → tasdiqlash → /ocr/api/branch/<id>/confirm/ → sahifa yangilanadi.
 * ────────────────────────────────────────────────────────────────────────── */
(() => {
  'use strict';

  const scriptTag = document.currentScript;
  const BRANCH_ID = scriptTag?.dataset?.branchId;
  if (!BRANCH_ID) { console.error('receipt_ocr: data-branch-id yo\'q'); return; }

  const SCAN_URL    = `/ocr/api/branch/${BRANCH_ID}/scan/`;
  const CONFIRM_URL = `/ocr/api/branch/${BRANCH_ID}/confirm/`;

  let PRODUCTS = [];   // scan javobidan keladi
  let ROWS     = [];   // hozirgi tahrirlanayotgan qatorlar

  const getCsrf = () =>
    (document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/) || [])[1] || '';

  const money = v =>
    (Number(v) || 0).toLocaleString('uz-UZ') + " so'm";

  /* ── Modal HTML (loyihaning modal-veil uslubida) ──────────────────────── */
  function buildModal() {
    if (document.getElementById('rocrModal')) return;
    const veil = document.createElement('div');
    veil.className = 'modal-veil d-none';
    veil.id = 'rocrModal';
    veil.innerHTML = `
      <div class="modal-sheet rocr-sheet">
        <div class="rocr-head">
          <div class="rocr-title"><i class="fa fa-camera me-2"></i>Chekdan xarid</div>
          <button class="sheet-close" id="rocrClose"><i class="fa fa-times"></i></button>
        </div>

        <!-- 1-QADAM: rasm tanlash -->
        <div class="rocr-step" id="rocrStepUpload">
          <div class="rocr-hint">
            Chekni <b>tekis joyda</b>, yaxshi yorug'likda, to'liq sig'dirib rasmga oling —
            aniqlik shunga bog'liq.
          </div>
          <input type="file" id="rocrFile" accept="image/*" capture="environment" hidden>
          <div class="rocr-upload-btns">
            <button class="btn btn-primary" id="rocrPickCam">
              <i class="fa fa-camera me-1"></i> Rasmga olish
            </button>
            <button class="btn btn-secondary" id="rocrPickFile">
              <i class="fa fa-image me-1"></i> Galereyadan
            </button>
          </div>
          <img id="rocrPreview" class="rocr-preview d-none" alt="">
          <button class="btn btn-primary w-100 d-none" id="rocrScanBtn">
            <i class="fa fa-magnifying-glass me-1"></i> O'qish (OCR)
          </button>
          <div class="rocr-loading d-none" id="rocrLoading">
            <i class="fa fa-spinner fa-spin me-2"></i>Chek o'qilmoqda, biroz kuting...
          </div>
          <div class="rocr-error d-none" id="rocrError"></div>
        </div>

        <!-- 2-QADAM: natijani tekshirish/tahrirlash -->
        <div class="rocr-step d-none" id="rocrStepReview">
          <div class="rocr-hint">
            O'qilgan qatorlarni tekshiring: mahsulotni tanlang, miqdor va tan
            narxni to'g'rilang. Keraksiz qatorni <i class="fa fa-trash-can"></i> bilan o'chiring.
          </div>
          <div class="rocr-rows" id="rocrRows"></div>
          <button class="btn btn-secondary w-100" id="rocrAddRow" style="margin-top:8px">
            <i class="fa fa-plus me-1"></i> Qator qo'shish
          </button>
          <div class="rocr-total" id="rocrTotal"></div>
          <details class="rocr-raw">
            <summary>OCR xom matnini ko'rish</summary>
            <pre id="rocrRawText"></pre>
          </details>
          <div class="rocr-error d-none" id="rocrError2"></div>
          <div class="rocr-actions">
            <button class="btn btn-secondary" id="rocrRetry">
              <i class="fa fa-rotate-left me-1"></i> Qayta olish
            </button>
            <button class="btn btn-primary" id="rocrConfirm">
              <i class="fa fa-check me-1"></i> Tasdiqlash
            </button>
          </div>
        </div>
      </div>`;
    document.body.appendChild(veil);

    veil.addEventListener('click', e => { if (e.target === veil) close(); });
    document.getElementById('rocrClose').onclick    = close;
    document.getElementById('rocrPickCam').onclick  = () => pickImage(true);
    document.getElementById('rocrPickFile').onclick = () => pickImage(false);
    document.getElementById('rocrFile').onchange    = onFileChosen;
    document.getElementById('rocrScanBtn').onclick  = scan;
    document.getElementById('rocrRetry').onclick    = resetToUpload;
    document.getElementById('rocrAddRow').onclick   = () => { ROWS.push(emptyRow()); renderRows(); };
    document.getElementById('rocrConfirm').onclick  = confirmRows;
  }

  const open  = () => { buildModal(); resetToUpload();
                        document.getElementById('rocrModal').classList.remove('d-none'); };
  const close = () => document.getElementById('rocrModal')?.classList.add('d-none');

  /* ── 1-qadam: rasm ────────────────────────────────────────────────────── */
  let chosenFile = null;

  function pickImage(useCamera) {
    const inp = document.getElementById('rocrFile');
    if (useCamera) inp.setAttribute('capture', 'environment');
    else           inp.removeAttribute('capture');
    inp.value = '';
    inp.click();
  }

  function onFileChosen(e) {
    chosenFile = e.target.files[0] || null;
    if (!chosenFile) return;
    const img = document.getElementById('rocrPreview');
    img.src = URL.createObjectURL(chosenFile);
    img.classList.remove('d-none');
    document.getElementById('rocrScanBtn').classList.remove('d-none');
    hideError();
  }

  function resetToUpload() {
    chosenFile = null;
    document.getElementById('rocrStepReview').classList.add('d-none');
    document.getElementById('rocrStepUpload').classList.remove('d-none');
    document.getElementById('rocrPreview').classList.add('d-none');
    document.getElementById('rocrScanBtn').classList.add('d-none');
    document.getElementById('rocrLoading').classList.add('d-none');
    hideError();
  }

  function showError(msg, second = false) {
    const el = document.getElementById(second ? 'rocrError2' : 'rocrError');
    el.textContent = msg;
    el.classList.remove('d-none');
  }
  function hideError() {
    document.getElementById('rocrError')?.classList.add('d-none');
    document.getElementById('rocrError2')?.classList.add('d-none');
  }

  /* ── Scan (OCR) ───────────────────────────────────────────────────────── */
  async function scan() {
    if (!chosenFile) return;
    hideError();
    document.getElementById('rocrScanBtn').disabled = true;
    document.getElementById('rocrLoading').classList.remove('d-none');

    try {
      const fd = new FormData();
      fd.append('image', chosenFile);
      const resp = await fetch(SCAN_URL, {
        method: 'POST',
        headers: { 'X-CSRFToken': getCsrf() },
        body: fd,
      });
      const data = await resp.json();
      if (!resp.ok || data.status !== 'ok') {
        showError(data.message || `Xatolik (${resp.status})`);
        return;
      }

      PRODUCTS = data.products || [];
      ROWS = (data.rows || []).map(r => ({
        product_id: r.product_id || '',
        quantity:   r.qty   || '1',
        cost_price: r.price || '',
        mode:       'unit',   // pastda defaultMode bilan to'g'rilanadi
        raw:        r.raw   || '',
        score:      r.score || 0,
      }));
      // Moslashgan mahsulot karobkali bo'lsa — rejim avtomatik 'karobka'
      ROWS.forEach(r => { r.mode = defaultMode(r.product_id); });
      if (!ROWS.length) ROWS.push(emptyRow());

      document.getElementById('rocrRawText').textContent = data.raw_text || '';
      document.getElementById('rocrStepUpload').classList.add('d-none');
      document.getElementById('rocrStepReview').classList.remove('d-none');
      renderRows();
    } catch (err) {
      showError('Tarmoq xatosi: ' + err.message);
    } finally {
      document.getElementById('rocrScanBtn').disabled = false;
      document.getElementById('rocrLoading').classList.add('d-none');
    }
  }

  /* ── 2-qadam: qatorlar jadvali ───────────────────────────────────────── */
  const emptyRow = () =>
    ({ product_id: '', quantity: '1', cost_price: '', mode: 'unit', raw: '', score: 0 });

  const productById = id => PRODUCTS.find(p => String(p.id) === String(id));

  // Karobkali mahsulot uchun DEFAULT rejim — 'box' (kompaniya cheki karobka
  // hisobida keladi), oddiy mahsulot uchun 'unit' (dona/kg).
  const defaultMode = productId => {
    const p = productById(productId);
    return (p && p.box_enabled) ? 'box' : 'unit';
  };

  function renderRows() {
    const wrap = document.getElementById('rocrRows');
    wrap.innerHTML = '';

    ROWS.forEach((row, idx) => {
      const prod = productById(row.product_id);
      const div  = document.createElement('div');
      div.className = 'rocr-row' + (row.product_id ? '' : ' rocr-row-warn');

      const options = ['<option value="">— Mahsulot tanlang —</option>']
        .concat(PRODUCTS.map(p =>
          `<option value="${p.id}" ${String(p.id) === String(row.product_id) ? 'selected' : ''}>
             ${escapeHtml(p.name)}</option>`))
        .join('');

      const modeSel = prod && prod.box_enabled
        ? `<select class="rocr-mode" data-i="${idx}">
             <option value="unit" ${row.mode === 'unit' ? 'selected' : ''}>${escapeHtml(prod.unit)}</option>
             <option value="box"  ${row.mode === 'box'  ? 'selected' : ''}>Karobka (${prod.units_per_box})</option>
           </select>`
        : `<span class="rocr-unit">${prod ? escapeHtml(prod.unit) : ''}</span>`;

      div.innerHTML = `
        ${row.raw ? `<div class="rocr-raw-line" title="Chekdan o'qilgan qator">${escapeHtml(row.raw)}</div>` : ''}
        <div class="rocr-row-grid">
          <select class="rocr-product" data-i="${idx}">${options}</select>
          <input type="number" class="rocr-qty" data-i="${idx}" min="0" step="any"
                 value="${escapeHtml(row.quantity)}" placeholder="Miqdor">
          ${modeSel}
          <input type="number" class="rocr-price" data-i="${idx}" min="0" step="any"
                 value="${escapeHtml(row.cost_price)}"
                 placeholder="${row.mode === 'box' ? 'Narx (1 karobka)' : 'Narx (1 ' + (prod ? prod.unit : 'dona') + ')'}">
          <button class="rocr-del" data-i="${idx}" title="O'chirish">
            <i class="fa fa-trash-can"></i>
          </button>
        </div>`;
      wrap.appendChild(div);
    });

    // Event delegation
    wrap.querySelectorAll('.rocr-product').forEach(el => el.onchange = e => {
      const i = +e.target.dataset.i;
      ROWS[i].product_id = e.target.value;
      // Narx bo'sh bo'lsa — mahsulotning oxirgi tan narxini taklif qilamiz
      const p = productById(e.target.value);
      if (p && !ROWS[i].cost_price && p.last_cost) ROWS[i].cost_price = p.last_cost;
      ROWS[i].mode = defaultMode(e.target.value);
      renderRows();
    });
    wrap.querySelectorAll('.rocr-qty').forEach(el => el.oninput = e => {
      ROWS[+e.target.dataset.i].quantity = e.target.value; updateTotal();
    });
    wrap.querySelectorAll('.rocr-price').forEach(el => el.oninput = e => {
      ROWS[+e.target.dataset.i].cost_price = e.target.value; updateTotal();
    });
    wrap.querySelectorAll('.rocr-mode').forEach(el => el.onchange = e => {
      ROWS[+e.target.dataset.i].mode = e.target.value;
      renderRows();   // placeholder ("1 karobka" / "1 dona") yangilansin
    });
    wrap.querySelectorAll('.rocr-del').forEach(el => el.onclick = e => {
      ROWS.splice(+e.currentTarget.dataset.i, 1);
      if (!ROWS.length) ROWS.push(emptyRow());
      renderRows();
    });

    updateTotal();
  }

  function rowTotal(row) {
    const qty   = parseFloat(row.quantity)   || 0;
    const price = parseFloat(row.cost_price) || 0;
    // Karobka rejimida narx — 1 KAROBKA narxi (chekdagidek): jami = soni x narx.
    // Unit rejimida narx — 1 dona/kg narxi: jami = miqdor x narx.
    return qty * price;
  }

  function updateTotal() {
    const total = ROWS.reduce((s, r) => s + rowTotal(r), 0);
    document.getElementById('rocrTotal').textContent = 'Jami: ' + money(total);
  }

  /* ── Tasdiqlash ───────────────────────────────────────────────────────── */
  async function confirmRows() {
    hideError();
    const valid = ROWS.filter(r => r.product_id);
    if (!valid.length) { showError('Kamida bitta mahsulot tanlang.', true); return; }

    const btn = document.getElementById('rocrConfirm');
    btn.disabled = true;
    btn.innerHTML = '<i class="fa fa-spinner fa-spin me-1"></i> Kiritilmoqda...';

    try {
      const resp = await fetch(CONFIRM_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrf(),
        },
        body: JSON.stringify({ rows: valid }),
      });
      const data = await resp.json();

      if (!resp.ok || data.status !== 'ok') {
        showError(data.message || `Xatolik (${resp.status})`, true);
        return;
      }

      let msg = `${data.created_count} qator kiritildi. Jami: ${money(data.grand_total)}.`;
      if (data.errors && data.errors.length) {
        msg += '\nOgohlantirishlar:\n' + data.errors.join('\n');
      }
      alert(msg);
      location.reload();   // qoldiq/qarz yangilangan holda sahifa qayta ochiladi
    } catch (err) {
      showError('Tarmoq xatosi: ' + err.message, true);
    } finally {
      btn.disabled = false;
      btn.innerHTML = '<i class="fa fa-check me-1"></i> Tasdiqlash';
    }
  }

  /* ── Yordamchi ────────────────────────────────────────────────────────── */
  function escapeHtml(s) {
    return String(s ?? '').replace(/[&<>"']/g, c =>
      ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  }

  /* ── Ishga tushirish ──────────────────────────────────────────────────── */
  document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('openReceiptOcr')?.addEventListener('click', open);
  });
})();
