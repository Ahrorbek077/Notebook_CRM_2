/**
 * receipt.js
 * ──────────────────────────────────────────────────────────────────────────
 * NoteBook — Chek chiqarish moduli
 *
 * Imkoniyatlar:
 *   1. Browser Print  — CSS @media print orqali
 *   2. PDF yuklab olish — jsPDF orqali
 *   3. Bluetooth Printer — Web Bluetooth API + ESC/POS (58mm)
 *
 * Ishlatish:
 *   ReceiptManager.print(saleId)            → chek modalini ochadi
 *   ReceiptManager.printBluetooth(saleId)   → to'g'ridan Bluetooth printer
 * ──────────────────────────────────────────────────────────────────────────
 */

const ReceiptManager = (() => {

  // ── ESC/POS konstantalari (80mm, 48 belgi) ────────────────────────────────
  const ESC = 0x1B;
  const GS  = 0x1D;
  const ESC_POS = {
    INIT:           [ESC, 0x40],
    ALIGN_LEFT:     [ESC, 0x61, 0x00],
    ALIGN_CENTER:   [ESC, 0x61, 0x01],
    ALIGN_RIGHT:    [ESC, 0x61, 0x02],
    BOLD_ON:        [ESC, 0x45, 0x01],
    BOLD_OFF:       [ESC, 0x45, 0x00],
    DOUBLE_HEIGHT:  [GS,  0x21, 0x10],
    NORMAL_SIZE:    [GS,  0x21, 0x00],
    LINE_FEED:      [0x0A],
    CUT_PAPER:      [GS,  0x56, 0x41, 0x03],  // partial cut
    CHARSET_CP866:  [ESC, 0x74, 0x11],         // ESC t 17 — Cyrillic #2 (CP866),
                                                // deyarli barcha ESC/POS klon
                                                // printerlarda Kirill uchun standart
  };

  const COL_WIDTH   = 32;  // 58mm ≈ 32 belgi (xitoylik arzon termo-printerlar standarti)
  const DIVIDER     = '-'.repeat(COL_WIDTH);  // oddiy ASCII chiziq — har qanday kodlashda to'g'ri chiqadi

  // ── Yordamchi: matn o'rtaga hizalash ─────────────────────────────────────
  function center(text, width = COL_WIDTH) {
    if (text.length >= width) return text;
    const pad = Math.floor((width - text.length) / 2);
    return ' '.repeat(pad) + text;
  }

  // ── Yordamchi: ikki ustun (nomi + narxi) ─────────────────────────────────
  function twoCol(left, right, width = COL_WIDTH) {
    const space = width - left.length - right.length;
    if (space < 1) return left.substring(0, width - right.length - 1) + ' ' + right;
    return left + ' '.repeat(space) + right;
  }

  // ── Pul formati ───────────────────────────────────────────────────────────
  function fmt(num) {
    return Number(num).toLocaleString('uz-UZ') + " so'm";
  }

  // ── Miqdor formati: "1.000" -> "1", "2.500" -> "2.5" ───────────────────────
  function fmtQty(val) {
    const n = parseFloat(val);
    if (isNaN(n)) return '0';
    return n % 1 === 0 ? n.toString() : n.toFixed(3).replace(/0+$/, '').replace(/\.$/, '');
  }

  // ── Ma'lumot yuklash ──────────────────────────────────────────────────────
  async function fetchReceipt(saleId) {
    const resp = await fetch(`/clients/receipt/${saleId}/`, {
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    });
    if (!resp.ok) throw new Error("Chek ma'lumoti yuklanmadi");
    const data = await resp.json();
    if (data.status !== 'success') throw new Error(data.message || "Xatolik");
    return data.receipt;
  }

  // ── CP866 (Cyrillic #2) kodlash jadvali ─────────────────────────────────
  // SABAB: termoprinterlar (xitoylik klon ESC/POS qurilmalar) UTF-8'ni
  // tushunmaydi — har bir Kirill harf UTF-8'da 2 bayt bo'lgani uchun,
  // printer ularni bitta-baytli kodlash deb noto'g'ri o'qib, "axlat"
  // belgilar chiqarib yuboradi (ikki baravar ko'payib). CP866 — bunday
  // printerlarning deyarli barchasida standart bo'lgan, bitta-baytli
  // Kirill kodlash jadvali (DOS-davridan qolgan, lekin hamon eng keng
  // qo'llab-quvvatlanadigan variant).
  const CP866_MAP = (() => {
    const map = {};
    for (let i = 0; i < 32; i++) map[0x0410 + i] = 0x80 + i;  // А-Я
    for (let i = 0; i < 16; i++) map[0x0430 + i] = 0xA0 + i;  // а-п
    for (let i = 0; i < 16; i++) map[0x0440 + i] = 0xE0 + i;  // р-я
    map[0x0401] = 0xF0; // Ё
    map[0x0451] = 0xF1; // ё
    return map;
  })();

  function encodeCp866(str) {
    const bytes = [];
    for (const ch of str) {
      const code = ch.codePointAt(0);
      if (code < 128) {
        bytes.push(code);
      } else if (CP866_MAP[code] !== undefined) {
        bytes.push(CP866_MAP[code]);
      } else {
        bytes.push(0x3F); // tushunarsiz belgi — '?'
      }
    }
    return new Uint8Array(bytes);
  }

  // ── ESC/POS bytes yaratish ────────────────────────────────────────────────
  function buildEscPos(receipt) {
    const chunks  = [];

    const push = (...cmds) => cmds.forEach(c => {
      chunks.push(Array.isArray(c) ? new Uint8Array(c) : encodeCp866(c));
    });

    // Printer reset + Kirill kodlash jadvalini yoqish
    push(ESC_POS.INIT, ESC_POS.CHARSET_CP866);

    // ── Sarlavha ─────────────────────────────────────────────────────────────
    push(ESC_POS.ALIGN_CENTER, ESC_POS.BOLD_ON, ESC_POS.DOUBLE_HEIGHT);
    push(`${receipt.business_name || 'Biznes'}\n`);
    push(ESC_POS.NORMAL_SIZE, ESC_POS.BOLD_OFF);
    push(`Sotuv cheki #${receipt.sale_id}\n`);
    push(DIVIDER + '\n');

    // ── Telefon va kassir (maxfiylik uchun ism/qarz ko'rsatilmaydi) ───────────
    push(ESC_POS.ALIGN_LEFT);
    push(`Tel   : ${receipt.client_phone}\n`);
    push(`Kassir: ${receipt.cashier}\n`);
    push(`Sana  : ${receipt.date}\n`);
    push(DIVIDER + '\n');

    // ── Ustun sarlavhasi ──────────────────────────────────────────────────────
    push(ESC_POS.BOLD_ON);
    push(twoCol('Mahsulot (dona)', 'Summa') + '\n');
    push(ESC_POS.BOLD_OFF);
    push(DIVIDER + '\n');

    // ── Mahsulotlar ───────────────────────────────────────────────────────────
    receipt.items.forEach(item => {
      const nameLine = `${item.name}`;
      // Uzun nomlar uchun qisqartirish
      const shortName = nameLine.length > 28 ? nameLine.substring(0, 26) + '..' : nameLine;
      const qtyPrice  = `${fmtQty(item.qty)}x${fmt(item.price)}`;
      push(twoCol(shortName, fmt(item.subtotal)) + '\n');
      push(`  ${qtyPrice}\n`);
    });

    push(DIVIDER + '\n');

    // ── Jami ──────────────────────────────────────────────────────────────────
    push(ESC_POS.BOLD_ON);
    push(twoCol('JAMI:', fmt(receipt.total)) + '\n');
    push(ESC_POS.BOLD_OFF);

    // ── Footer ────────────────────────────────────────────────────────────────
    push(DIVIDER + '\n');
    push(ESC_POS.ALIGN_CENTER);
    push('Xarid uchun rahmat!\n');
    push(`${receipt.business_name || 'Biznes'}\n`);

    // 3 bo'sh qator + kesish
    push('\n\n\n');
    push(ESC_POS.CUT_PAPER);

    // Umumiy buffer
    const totalLen = chunks.reduce((s, c) => s + c.length, 0);
    const buffer   = new Uint8Array(totalLen);
    let offset     = 0;
    chunks.forEach(c => { buffer.set(c, offset); offset += c.length; });
    return buffer;
  }

  // ── HTML chek (modal va print uchun) ─────────────────────────────────────
  function buildHtml(receipt) {
    const itemsHtml = receipt.items.map(item => `
      <tr>
        <td>${item.name}</td>
        <td class="text-center">${fmtQty(item.qty)}</td>
        <td class="text-end">${Number(item.price).toLocaleString('uz-UZ')}</td>
        <td class="text-end">${Number(item.subtotal).toLocaleString('uz-UZ')}</td>
      </tr>
    `).join('');

    const rowStyle = "display:flex;justify-content:space-between;padding:4px 0;font-size:.82rem;border-bottom:1px solid var(--b,rgba(255,255,255,.06))";
    const labelStyle = "color:var(--t2,#aaa)";
    const valueStyle = "color:var(--t,#fff);font-weight:600";

    return `
      <div id="receiptContent" style="font-family:var(--mono,'Courier New',monospace)">

        <!-- Sarlavha -->
        <div style="text-align:center;margin-bottom:14px">
          <div style="font-size:1.1rem;font-weight:800;color:var(--cyan,#00bcd4);letter-spacing:.05em">${receipt.business_name || 'Biznes'}</div>
          <div style="font-size:.75rem;color:var(--t3,#666);margin-top:2px">Sotuv cheki #${receipt.sale_id}</div>
          <div style="height:1px;background:var(--b,rgba(255,255,255,.08));margin:10px 0"></div>
        </div>

        <!-- Telefon/kassir info (maxfiylik uchun ism/qarz ko'rsatilmaydi) -->
        <div style="margin-bottom:12px">
          <div style="${rowStyle}"><span style="${labelStyle}">Telefon</span><span style="${valueStyle}">${receipt.client_phone}</span></div>
          <div style="${rowStyle}"><span style="${labelStyle}">Kassir</span><span style="color:var(--t,#fff)">${receipt.cashier}</span></div>
          <div style="${rowStyle};border:none"><span style="${labelStyle}">Sana</span><span style="color:var(--t,#fff)">${receipt.date}</span></div>
        </div>

        <div style="height:1px;background:var(--b,rgba(255,255,255,.08));margin-bottom:10px"></div>

        <!-- Ustun sarlavha -->
        <div style="display:flex;justify-content:space-between;font-size:.72rem;color:var(--t3,#666);
                    padding:0 0 6px;border-bottom:1px solid var(--b,rgba(255,255,255,.08));margin-bottom:4px">
          <span style="flex:2">Mahsulot</span>
          <span style="flex:1;text-align:center">Dona</span>
          <span style="flex:1;text-align:right">Narx</span>
          <span style="flex:1;text-align:right">Jami</span>
        </div>

        <!-- Mahsulotlar -->
        ${receipt.items.map(item => `
          <div style="display:flex;justify-content:space-between;padding:5px 0;
                      font-size:.8rem;border-bottom:1px solid var(--b,rgba(255,255,255,.04))">
            <span style="flex:2;color:var(--t,#fff);padding-right:6px">${item.name}</span>
            <span style="flex:1;text-align:center;color:var(--t2,#aaa)">${fmtQty(item.qty)}</span>
            <span style="flex:1;text-align:right;color:var(--t2,#aaa)">${Number(item.price).toLocaleString('uz-UZ')}</span>
            <span style="flex:1;text-align:right;color:var(--amber,#ffab00);font-weight:700">${Number(item.subtotal).toLocaleString('uz-UZ')}</span>
          </div>
        `).join('')}

        <div style="height:1px;background:var(--b,rgba(255,255,255,.08));margin:10px 0"></div>

        <!-- Jami -->
        <div style="display:flex;justify-content:space-between;padding:6px 0;font-size:.9rem">
          <span style="font-weight:800;color:var(--t,#fff)">JAMI</span>
          <span style="font-weight:800;color:var(--cyan,#00bcd4)">${Number(receipt.total).toLocaleString('uz-UZ')} so'm</span>
        </div>

        <!-- Balans satri olib tashlandi (maxfiylik) -->

        <div style="height:1px;background:var(--b,rgba(255,255,255,.08));margin:10px 0"></div>
        <div style="text-align:center;font-size:.72rem;color:var(--t3,#555)">Xarid uchun rahmat! · ${receipt.business_name || 'Biznes'}</div>
      </div>
    `;
  }

  // ── Modal ko'rsatish (modal-veil sistema) ───────────────────────────────
  function showModal(receipt) {
    document.getElementById('receiptModal')?.remove();

    const bluetoothBtn = window.isBluetoothSupported()
      ? `<button class="btn btn-primary" onclick="ReceiptManager.doBluetooth(${receipt.sale_id})"
               style="flex:1;height:36px;font-size:.82rem;min-width:80px">
           <i class="fa fa-bluetooth-b me-1"></i>Printer
         </button>`
      : '';

    // "Ulashish" — Eleph Label kabi o'z protokoliga ega "label printer"
    // ilovalariga PDF'ni to'g'ridan-to'g'ri yuborish uchun (Bluetooth tugmasi
    // ESC/POS bo'lmagan printerlar bilan ishlamaganda shu yo'l qo'l keladi)
    const shareSupported = !!(navigator.share && navigator.canShare);
    const shareBtn = shareSupported
      ? `<button class="btn btn-secondary" onclick="ReceiptManager.doShare(${receipt.sale_id})"
               style="flex:1;height:36px;font-size:.82rem;min-width:80px">
           <i class="fa fa-share-nodes me-1"></i>Ulashish
         </button>`
      : '';

    const html = `
      <div id="receiptModal"
           style="position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:9000;
                  display:flex;align-items:flex-end;justify-content:center">
        <div style="width:100%;max-width:480px;border-radius:18px 18px 0 0;
                    background:var(--bg-card,#1e1e2e);border-top:1px solid var(--b,rgba(255,255,255,.08));
                    max-height:90dvh;display:flex;flex-direction:column;">

          <div style="width:36px;height:4px;border-radius:2px;background:var(--b,rgba(255,255,255,.15));
                      margin:10px auto 0;flex-shrink:0"></div>

          <div style="display:flex;align-items:center;justify-content:space-between;
                      padding:12px 16px 8px;flex-shrink:0;border-bottom:1px solid var(--b,rgba(255,255,255,.08))">
            <span style="font-weight:700;font-size:.95rem;color:var(--t,#fff)">
              <i class="fa fa-receipt me-2" style="color:var(--cyan,#00bcd4)"></i>Chek #${receipt.sale_id}
            </span>
            <button onclick="ReceiptManager.closeModal()"
                    style="background:none;border:none;color:var(--t2,#aaa);font-size:1.1rem;cursor:pointer;padding:4px">
              <i class="fa fa-times"></i>
            </button>
          </div>

          <div style="overflow-y:auto;flex:1;padding:16px">
            ${buildHtml(receipt)}
          </div>

          <div style="display:flex;gap:8px;padding:12px 16px 20px;flex-shrink:0;
                      border-top:1px solid var(--b,rgba(255,255,255,.08));flex-wrap:wrap">
            <button class="btn btn-secondary" onclick="ReceiptManager.doPrint()"
                    style="flex:1;height:36px;font-size:.82rem;min-width:80px">
              <i class="fa fa-print me-1"></i>Chop
            </button>
            <button class="btn btn-secondary" onclick="ReceiptManager.doPdf(${receipt.sale_id})"
                    style="flex:1;height:36px;font-size:.82rem;min-width:80px">
              <i class="fa fa-file-pdf me-1"></i>PDF
            </button>
            ${shareBtn}
            ${bluetoothBtn}
          </div>
        </div>
      </div>
    `;

    document.body.insertAdjacentHTML('beforeend', html);
    document.getElementById('receiptModal').addEventListener('click', (e) => {
      if (e.target.id === 'receiptModal') ReceiptManager.closeModal();
    });
  }

  // ── Modalni yopish ────────────────────────────────────────────────────────
  function closeModal() {
    document.getElementById('receiptModal')?.remove();
  }


  // ── Browser print ─────────────────────────────────────────────────────────
  function doPrint() {
    const content = document.getElementById('receiptContent');
    if (!content) return;
    const printWin = window.open('', '_blank', 'width=400,height=600');
    printWin.document.write(`
      <!DOCTYPE html><html><head>
        <title>Chek</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
        <style>
          body { font-family: 'Courier New', monospace; font-size: 12px; margin: 0; padding: 10px; }
          .receipt-wrapper { max-width: 320px; margin: 0 auto; }
          @media print {
            body { -webkit-print-color-adjust: exact; }
          }
        </style>
      </head><body>${content.outerHTML}
        <script>window.onload=()=>{window.print();window.close();}<\/script>
      </body></html>
    `);
    printWin.document.close();
  }

  // ── PDF yuklab olish — SERVERDA generatsiya qilinadi (Kirill/o'zbek
  //    harflari to'liq chiqishi uchun; jsPDF standart shriftlari kirillni
  //    bilmaydi, shu sabab avval chek deyarli bo'sh chiqardi) ─────────────
  async function doPdf(saleId) {
    try {
      window.location.href = `/clients/receipt/${saleId}/pdf/`;
    } catch (err) {
      showToast('PDF xatoligi: ' + err.message, 'danger');
    }
  }

  // ── "Ulashish" — telefonning umumiy Share menyusi orqali RASM (PNG)
  //    yuboradi — to'g'ridan-to'g'ri boshqa ilovaga (masalan "Eleph Label",
  //    "Print Master" va h.k. — o'z protokoliga ega "label printer"
  //    ilovalari). MUHIM: PDF emas, aynan PNG (rasm) yuboramiz — chunki
  //    bunday "label" ilovalari deyarli har doim faqat rasm formatini
  //    tushunadi, PDF'ni ochib bera olmaydi (shu sabab avval "oq ekran"
  //    chiqqan edi). Bu — eng oson yo'l: faylni qo'lda yuklab olib, fayl
  //    menejeridan qidirib ochishning o'rnini bosadi. Faqat HTTPS'da va
  //    asosan Android Chrome'da ishlaydi. ──────────────────────────────
  async function doShare(saleId) {
    if (!navigator.share || !navigator.canShare) {
      showToast("Bu brauzer ulashishni qo'llab-quvvatlamaydi. PDF tugmasidan foydalaning.", 'warning');
      return;
    }
    try {
      showToast('Tayyorlanmoqda...', 'info');
      const resp = await fetch(`/clients/receipt/${saleId}/png/`);
      if (!resp.ok) throw new Error('Chekni yuklab bo\'lmadi');
      const blob = await resp.blob();
      const file = new File([blob], `chek_${saleId}.png`, { type: 'image/png' });

      if (!navigator.canShare({ files: [file] })) {
        showToast("Bu qurilmada fayl ulashish ishlamaydi. PDF tugmasidan foydalaning.", 'warning');
        return;
      }

      await navigator.share({
        files: [file],
        title: `Chek #${saleId}`,
      });
    } catch (err) {
      // Foydalanuvchi ulashish oynasini bekor qilsa, bu ham xato sifatida keladi — uni e'tiborsiz qoldiramiz
      if (err.name !== 'AbortError') {
        showToast('Ulashishda xatolik: ' + err.message, 'danger');
      }
    }
  }

  // ── Web Bluetooth ESC/POS ─────────────────────────────────────────────────
  async function doBluetooth(saleId) {
    if (!navigator.bluetooth) {
      showToast(T.bluetooth_unsupported, 'warning');
      return;
    }
    try {
      showToast(T.printer_searching, 'info');

      // ESC/POS printerlari uchun GATT service UUID
      const PRINTER_SERVICE  = '000018f0-0000-1000-8000-00805f9b34fb';
      const PRINTER_CHAR     = '00002af1-0000-1000-8000-00805f9b34fb';

      const device = await navigator.bluetooth.requestDevice({
        filters: [
          { services: [PRINTER_SERVICE] },
        ],
        optionalServices: [PRINTER_SERVICE],
      }).catch(() => {
        // Agar filter ishlmasa — barcha qurilmalarni ko'rsat
        return navigator.bluetooth.requestDevice({
          acceptAllDevices: true,
          optionalServices: [PRINTER_SERVICE],
        });
      });

      showToast(`${device.name || 'Printer'} ga ulanmoqda...`, 'info');
      const server  = await device.gatt.connect();
      const service = await server.getPrimaryService(PRINTER_SERVICE);
      const char    = await service.getCharacteristic(PRINTER_CHAR);

      const receipt = await fetchReceipt(saleId);
      const bytes   = buildEscPos(receipt);

      // Katta ma'lumotni chunk qilib yuborish (BLE MTU = 512 bytes)
      const CHUNK = 512;
      for (let i = 0; i < bytes.length; i += CHUNK) {
        await char.writeValueWithoutResponse(bytes.slice(i, i + CHUNK));
        await new Promise(r => setTimeout(r, 20)); // kichik delay
      }

      await server.disconnect();
      showToast(T.receipt_printed, 'success');

    } catch (err) {
      if (err.name === 'NotFoundError' || err.name === 'AbortError') {
        // Foydalanuvchi bekor qildi
        return;
      }
      console.error('Bluetooth xatoligi:', err);
      showToast(`Printer xatoligi: ${err.message}`, 'danger');
    }
  }

  // ── Script dinamik yuklash ────────────────────────────────────────────────
  function loadScript(src) {
    return new Promise((resolve, reject) => {
      if (document.querySelector(`script[src="${src}"]`)) { resolve(); return; }
      const s = document.createElement('script');
      s.src = src; s.onload = resolve; s.onerror = reject;
      document.head.appendChild(s);
    });
  }

  // ── Toast ─────────────────────────────────────────────────────────────────
  function showToast(msg, type = 'info') {
    // Mavjud toast container yoki yangi
    let container = document.getElementById('receiptToastContainer');
    if (!container) {
      container = document.createElement('div');
      container.id = 'receiptToastContainer';
      container.style.cssText = 'position:fixed;bottom:1rem;right:1rem;z-index:9999;';
      document.body.appendChild(container);
    }
    const id   = 'toast_' + Date.now();
    const icon = { success: '✅', danger: '❌', warning: '⚠️', info: 'ℹ️' }[type] || 'ℹ️';
    container.insertAdjacentHTML('beforeend', `
      <div id="${id}" class="toast align-items-center text-bg-${type} border-0 show mb-2" role="alert">
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
  return {
    // Modalni ochadi (barcha variant tugmalari bilan)
    async print(saleId) {
      try {
        showToast(T.receipt_loading, 'info');
        const receipt = await fetchReceipt(saleId);
        showModal(receipt);
      } catch (err) {
        showToast('Chek yuklanmadi: ' + err.message, 'danger');
      }
    },

    // To'g'ridan Bluetooth (modal ochmasdan)
    async printBluetooth(saleId) {
      await doBluetooth(saleId);
    },

    // Modal ichidagi tugmalar uchun
    doPrint,
    doPdf,
    doShare,
    async doBluetooth(saleId) { await doBluetooth(saleId); },
    closeModal,
  };

})();

// ── Bluetooth qo'llab-quvvatlash tekshiruvi ──────────────────────────────────
window.isBluetoothSupported = () => !!navigator.bluetooth;