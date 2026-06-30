/**
 * receipt.js
 * ──────────────────────────────────────────────────────────────────────────
 * NoteBook — Chek chiqarish moduli
 *
 * Imkoniyatlar:
 *   1. RawBT (Android)  — ENG ISHONCHLI: ESC/POS ni RawBT ilovasiga yuboradi,
 *                         ilova Bluetooth ulanish/oqim nazoratini O'ZI qiladi
 *   2. Browser Print    — CSS @media print orqali
 *   3. PDF yuklab olish — serverda generatsiya
 *   4. Bluetooth Printer — Web Bluetooth API + ESC/POS (zaxira yo'l)
 *
 * MUHIM: printer 58mm (32 belgi). NT-2880 kabi arzon printerlarda Web Bluetooth
 * ko'pincha chala chiqaradi (header'dan keyin uziladi). RawBT yo'li shu muammoni
 * butunlay hal qiladi.
 *
 * Ishlatish:
 *   ReceiptManager.print(saleId)            → chek modalini ochadi
 *   ReceiptManager.printRawBT(saleId)       → to'g'ridan RawBT (Android)
 *   ReceiptManager.printBluetooth(saleId)   → to'g'ridan Web Bluetooth
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
  };

  const COL_WIDTH   = 32;  // 58mm ≈ 32 belgi (384 nuqta, A shrift). MUHIM: bu printer 58mm!
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

  // ── Pul formati (qisqa, "so'm"siz) — 58mm tor qatorlar uchun ──────────────
  function num(val) {
    return Number(val).toLocaleString('uz-UZ');
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

  // ── Kirill → Lotin transliteratsiya ──────────────────────────────────────
  // SABAB: diagnostika orqali aniqlandiki, bu printer "ESC t" (kodlash
  // tanlash) buyrug'ini umuman tan olmaydi — u doim faqat qattiq
  // biriktirilgan LOTIN (CP437) jadvalidan foydalanadi. Demak Kirill
  // harflarni "to'g'ri kodlash" orqali chiqarish bu qurilmada IMKONSIZ.
  // Yechim: Kirill matnni avtomatik LOTIN harflarga o'giramiz (standart
  // o'zbekcha transliteratsiya), so'ng oddiy ASCII (0-127 oralig'i)
  // sifatida yuboramiz — bu diapazon BARCHA kodlash jadvallarida bir xil,
  // shuning uchun har qanday printerda, hech qanday "moslashtirishsiz"
  // to'g'ri chiqadi. Bonus: matn picture'dan ancha yengil — chop etish
  // bir necha soniyada tugaydi, Bluetooth ulanish "uzilib qolish" xavfi
  // deyarli yo'qoladi.
  const CYR_TO_LAT = {
    'А':'A','Б':'B','В':'V','Г':'G','Д':'D','Е':'E','Ё':'Yo','Ж':'J','З':'Z',
    'И':'I','Й':'Y','К':'K','Л':'L','М':'M','Н':'N','О':'O','П':'P','Р':'R',
    'С':'S','Т':'T','У':'U','Ф':'F','Х':'X','Ц':'Ts','Ч':'Ch','Ш':'Sh','Щ':'Sh',
    'Ъ':'','Ы':'I','Ь':'','Э':'E','Ю':'Yu','Я':'Ya',
    'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'yo','ж':'j','з':'z',
    'и':'i','й':'y','к':'k','л':'l','м':'m','н':'n','о':'o','п':'p','р':'r',
    'с':'s','т':'t','у':'u','ф':'f','х':'x','ц':'ts','ч':'ch','ш':'sh','щ':'sh',
    'ъ':'','ы':'i','ь':'','э':'e','ю':'yu','я':'ya',
    'Ў':"O'",'ў':"o'",'Қ':'Q','қ':'q','Ғ':"G'",'ғ':"g'",'Ҳ':'H','ҳ':'h',
  };

  function transliterate(str) {
    let out = '';
    for (const ch of str) {
      out += CYR_TO_LAT[ch] !== undefined ? CYR_TO_LAT[ch] : ch;
    }
    return out;
  }

  function encodeAsciiSafe(str) {
    const translit = transliterate(str);
    const bytes = [];
    for (const ch of translit) {
      const code = ch.codePointAt(0);
      bytes.push(code < 128 ? code : 0x3F); // baribir lotin bo'lmasa — '?'
    }
    return new Uint8Array(bytes);
  }

  // ── ESC/POS bytes yaratish ────────────────────────────────────────────────
  function buildEscPos(receipt) {
    const chunks  = [];

    const push = (...cmds) => cmds.forEach(c => {
      chunks.push(Array.isArray(c) ? new Uint8Array(c) : encodeAsciiSafe(c));
    });

    // Printer reset (kodlash buyrug'i endi kerak emas — hammasi lotin/ASCII)
    push(ESC_POS.INIT);

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
    push(twoCol('Mahsulot', 'Summa') + '\n');
    push(ESC_POS.BOLD_OFF);
    push(DIVIDER + '\n');

    // ── Mahsulotlar (58mm: nom alohida qatorda, pastida miqdor×narx .... jami) ─
    receipt.items.forEach(item => {
      const name      = String(item.name);
      const nameLine  = name.length > COL_WIDTH ? name.substring(0, COL_WIDTH - 1) + '.' : name;
      push(nameLine + '\n');
      const left      = `  ${fmtQty(item.qty)} x ${num(item.price)}`;
      push(twoCol(left, num(item.subtotal)) + '\n');
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

    // 5 bo'sh qator — qo'lda yirtish uchun joy.
    // MUHIM: avtomatik "qog'oz kesish" (CUT_PAPER) buyrug'i ATAYLAB
    // yuborilmaydi — ko'plab arzon printerlarda (jumladan NT-2880 kabi
    // avtomatik kesuvchisi yo'q modellarda) bu buyruq "kesuvchi xatosi"
    // sifatida qabul qilinib, printer o'zini xavfsizlik rejimida o'chirib
    // qo'yadi. Qog'oz arrasimon chetidan qo'lda yirtiladi.
    push('\n\n\n\n\n');

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

    // RawBT — Android uchun ASOSIY (eng ishonchli) chop etish tugmasi.
    const rawbtBtn = isAndroidDevice()
      ? `<button class="btn btn-success" onclick="ReceiptManager.doRawBT(${receipt.sale_id})"
               style="flex:1;height:36px;font-size:.82rem;min-width:80px">
           <i class="fa fa-receipt me-1"></i>Chek (RawBT)
         </button>`
      : '';

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
            <span style="font-weight:700;font-size:.95rem;color:var(--t,#fff)"
                  onclick="ReceiptManager._onTitleClick()">
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
            ${rawbtBtn}
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
  // ── Printerga ulanish (umumiy, bitta requestDevice chaqiruvi) ────────────
  const PRINTER_SERVICE  = '000018f0-0000-1000-8000-00805f9b34fb';
  const PRINTER_CHAR     = '00002af1-0000-1000-8000-00805f9b34fb';

  async function selectPrinterDevice() {
    // MUHIM: faqat BITTA requestDevice chaqiruvi — ikkinchi (zanjirlangan)
    // chaqiruv "Must be handling a user gesture" xatosiga olib kelardi,
    // chunki brauzer buni "foydalanuvchi bosishi emas" deb hisoblaydi.
    // Shuning uchun bu funksiya BITTA marta chaqiriladi; keyingi qayta
    // ulanishlar (agar uzilib qolsa) shu TANLANGAN qurilmaning o'zidan
    // foydalanadi — yangi tanlov oynasi OCHILMAYDI (kerak ham emas).
    return navigator.bluetooth.requestDevice({
      acceptAllDevices: true,
      optionalServices: [PRINTER_SERVICE],
    });
  }

  async function establishGattConnection(device) {
    showToast(`${device.name || 'Printer'} ga ulanmoqda...`, 'info');
    const server  = await device.gatt.connect();
    const service = await server.getPrimaryService(PRINTER_SERVICE);
    const char    = await service.getCharacteristic(PRINTER_CHAR);

    const props = {
      write: char.properties.write,
      writeWithoutResponse: char.properties.writeWithoutResponse,
      notify: char.properties.notify,
      indicate: char.properties.indicate,
    };
    console.log('Printer characteristic properties:', props);
    debugLog('Printer: ' + (device.name || '?') + ' | props: ' + JSON.stringify(props));

    return { server, char };
  }

  async function connectToPrinter() {
    const device = await selectPrinterDevice();
    const { server, char } = await establishGattConnection(device);
    return { device, server, char };
  }

  // ── Bayt massivini printerga, vaqt berib yuborish (umumiy) ───────────────
  // SABAB 1 (hajm): BLE ulanishlar odatda bir martada juda kichik hajmni
  // (ko'pincha atigi ~20 bayt) qabul qila oladi.
  // SABAB 2 (tezlik — MUHIM): termoprinter har bir qatorni jismonan bosib
  // chiqarishi (qizdirish + qog'ozni siljitish) Bluetooth orqali ma'lumot
  // yuborishdan SEZILARLI DARAJADA SEKINROQ. Agar ma'lumot printer
  // "ulgurishi"dan tezroq yuborilsa, uning ichki bufer to'lib-toshib,
  // qurilma xatoga uchrab o'zini o'chirib qo'yadi.
  async function writeBytesToPrinter(char, bytes, { lineAware = true } = {}) {
    const CHUNK         = 20;
    const DELAY_MS      = 80;    // har bo'lak orasi
    const LINE_DELAY_MS = 280;   // har \n dan keyin — printer jismonan bosib ulgursin
    const WARMUP_MS     = 500;   // INIT dan keyin printer "uyg'onishi" uchun
    const sleep = ms => new Promise(r => setTimeout(r, ms));

    // Arzon BLE printerlarda ENG mos yo'l — "javobsiz" yozish. Sababi: qator
    // jismonan bosilayotganda printer GATT'ga javob (ACK) qaytara olmaydi —
    // "javobli" yozish esa shu paytda osilib qoladi, retry to'planib firmware
    // xatoga uchraydi va o'chib qoladi (aynan "header'dan keyin o'chish" shu).
    // Oqim nazoratini O'ZIMIZ kichik bo'lak + kechikish bilan qilamiz.
    const noResp = char.properties.writeWithoutResponse;

    async function writeChunkWithRetry(chunk, attempt = 1) {
      try {
        if (noResp) await char.writeValueWithoutResponse(chunk);
        else        await char.writeValue(chunk);
      } catch (err) {
        debugLog(`Yozish xatosi (urinish ${attempt}): ${err.message}`);
        if (attempt < 5) {
          const isBusy = /already in progress/i.test(err.message);
          await sleep(isBusy ? 150 * attempt : 200 * attempt);
          return writeChunkWithRetry(chunk, attempt + 1);
        }
        throw err;
      }
    }

    await sleep(WARMUP_MS);   // MUHIM: INIT dan keyin printer tayyor bo'lsin

    const total = bytes.length;
    for (let i = 0; i < total; i += CHUNK) {
      const chunk = bytes.slice(i, i + CHUNK);
      await writeChunkWithRetry(chunk);
      const hasLineFeed = lineAware && chunk.includes(0x0A);
      await sleep(hasLineFeed ? LINE_DELAY_MS : DELAY_MS);
      if (total > 2000 && (i / CHUNK) % 100 === 0) {
        debugLog(`Yuborilmoqda: ${Math.round(i / total * 100)}%`);
      }
    }
  }

  // ── RawBT (Android) — ENG ISHONCHLI YO'L ─────────────────────────────────
  // RawBT ilovasi (ru.a402d.rawbtprinter) ESC/POS ma'lumotni base64 ko'rinishida
  // "rawbt:" sxema orqali qabul qiladi va Bluetooth ulanish + oqim nazoratini
  // O'ZI to'g'ri boshqaradi. Shu sabab NT-2880 kabi arzon printerlarda Web
  // Bluetooth'dan ancha barqaror — chek to'liq chiqadi, "header'dan keyin
  // o'chish" muammosi yo'qoladi. (Foydalanuvchi telefonida RawBT o'rnatilgan
  // bo'lishi kerak — Play Market: ru.a402d.rawbtprinter.)
  function bytesToBase64(bytes) {
    let bin = '';
    const STEP = 0x8000; // katta massivlarda "Maximum call stack" bo'lmasligi uchun
    for (let i = 0; i < bytes.length; i += STEP) {
      bin += String.fromCharCode.apply(null, bytes.subarray(i, i + STEP));
    }
    return btoa(bin);
  }

  function isAndroidDevice() {
    return /android/i.test(navigator.userAgent || '');
  }

  // ESC/POS baytlarni RawBT'ga yuborish. intent: sxema — agar RawBT o'rnatilmagan
  // bo'lsa, brauzer avtomatik Play Market sahifasini ochadi.
  function sendBytesToRawBT(bytes) {
    const b64 = bytesToBase64(bytes);
    const intentUrl =
      'intent:base64,' + b64 +
      '#Intent;scheme=rawbt;package=ru.a402d.rawbtprinter;end;';
    window.location.href = intentUrl;
  }

  async function doRawBT(saleId) {
    try {
      showToast('Chek tayyorlanmoqda...', 'info');
      const receipt = await fetchReceipt(saleId);
      const bytes   = buildEscPos(receipt);
      debugLog(`RawBT: ${bytes.length} bayt yuborilmoqda`);
      sendBytesToRawBT(bytes);
      showToast('RawBT ilovasiga yuborildi', 'success');
    } catch (err) {
      console.error('RawBT xatoligi:', err);
      showToast('RawBT xatoligi: ' + err.message + ". RawBT o'rnatilganini tekshiring.", 'danger');
    }
  }

  // ── Web Bluetooth ESC/POS (zaxira yo'l) ──────────────────────────────────
  async function doBluetooth(saleId) {
    if (!navigator.bluetooth) {
      showToast(T.bluetooth_unsupported, 'warning');
      return;
    }
    try {
      showToast(T.printer_searching, 'info');
      const device = await selectPrinterDevice();

      // MATN rejimi (yengil, tez) — Kirill harflar avtomatik LOTINGA
      // o'giriladi (qarang: transliterate/encodeAsciiSafe), shuning uchun
      // printerning kodlash jadvali AHAMIYATSIZ: faqat oddiy ASCII (0-127)
      // yuboriladi, bu har qanday qurilmada bir xil ishlaydi. Bonus:
      // ma'lumot hajmi rasmdan O'NLAB MARTA KICHIK — chop etish bir necha
      // soniyada tugaydi, Bluetooth "band/uzilib qolish" xavfi deyarli yo'q.
      const receipt = await fetchReceipt(saleId);
      const bytes   = buildEscPos(receipt);
      debugLog(`Chek matni tayyor: ${bytes.length} bayt (lotin harflarda)`);

      // ── Qayta ulanish bilan urinish ──────────────────────────────────────
      // Arzon printerlar jismonan bosib chiqarish paytida Bluetooth
      // ulanishini VAQTINCHA uzib qo'yishi keng tarqalgan holat. Bunday
      // holatda BUTUN jarayonni emas (yangi qurilma tanlash oynasi
      // ochilmasligi uchun), faqat ULANISHNI qayta tiklab, davom etamiz.
      const MAX_ATTEMPTS = 3;
      let lastErr = null;
      for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt++) {
        try {
          const { server, char } = await establishGattConnection(device);
          if (attempt > 1) {
            debugLog(`Qayta ulanish (${attempt}-urinish) — boshidan yuborilmoqda`);
            showToast(`Qayta ulanmoqda (${attempt}-urinish)...`, 'warning');
          }
          await writeBytesToPrinter(char, bytes, { lineAware: true });
          await new Promise(r => setTimeout(r, 300));
          try { await server.disconnect(); } catch (_) { /* allaqachon uzilgan bo'lishi mumkin */ }
          showToast(T.receipt_printed, 'success');
          lastErr = null;
          break;
        } catch (err) {
          lastErr = err;
          debugLog(`Urinish ${attempt} muvaffaqiyatsiz: ${err.message}`);
          if (attempt < MAX_ATTEMPTS) {
            await new Promise(r => setTimeout(r, 800));
          }
        }
      }
      if (lastErr) throw lastErr;

    } catch (err) {
      if (err.name === 'NotFoundError' || err.name === 'AbortError') {
        // Foydalanuvchi bekor qildi
        return;
      }
      console.error('Bluetooth xatoligi:', err);
      debugLog('XATO: ' + err.name + ' — ' + err.message);
      showToast(
        `Printer xatoligi: ${err.message}. "Ulashish" tugmasi orqali ham urinib ko'ring.`,
        'danger'
      );
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

  // ── Mobil debug panel — "F12" o'rniga ────────────────────────────────────
  // Telefonda Chrome DevTools (F12) ochish uchun kompyuter + USB sim kerak.
  // Shu panel orqali xabarlarni TO'G'RIDAN-TO'G'RI EKRANDA ko'rish mumkin —
  // shunchaki skrinshot olib yuborish kifoya.
  // Ochish: chek oynasidagi sarlavhani 5 marta ketma-ket bosing.
  const _debugLines = [];
  function debugLog(msg) {
    const time = new Date().toLocaleTimeString('uz-UZ');
    _debugLines.push(`[${time}] ${msg}`);
    if (_debugLines.length > 50) _debugLines.shift();
    const panel = document.getElementById('receiptDebugPanel');
    if (panel) panel.textContent = _debugLines.join('\n');
  }

  function toggleDebugPanel() {
    let panel = document.getElementById('receiptDebugPanel');
    if (panel) { panel.remove(); return; }
    panel = document.createElement('pre');
    panel.id = 'receiptDebugPanel';
    panel.style.cssText = `
      position:fixed; inset:auto 0 0 0; max-height:40vh; overflow-y:auto;
      background:#000; color:#0f0; font-size:10px; line-height:1.4;
      padding:8px; margin:0; z-index:99999; white-space:pre-wrap;
      font-family:monospace; border-top:2px solid #0f0;
    `;
    panel.textContent = _debugLines.length
      ? _debugLines.join('\n')
      : "Debug panel ochildi. Bluetooth/Printer harakatlari shu yerda ko'rinadi.";
    document.body.appendChild(panel);
  }

  // 5 marta bosish bilan ochish/yopish (chek oyna sarlavhasiga ulanadi — pastda)
  let _titleClickCount = 0;
  let _titleClickTimer = null;
  function _onTitleClickForDebug() {
    _titleClickCount++;
    clearTimeout(_titleClickTimer);
    _titleClickTimer = setTimeout(() => { _titleClickCount = 0; }, 1500);
    if (_titleClickCount >= 5) {
      _titleClickCount = 0;
      toggleDebugPanel();
    }
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
    debugLog(`[${type}] ${msg}`);
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

    // To'g'ridan RawBT (Android — eng ishonchli, modal ochmasdan)
    async printRawBT(saleId) {
      await doRawBT(saleId);
    },

    // To'g'ridan Bluetooth (modal ochmasdan)
    async printBluetooth(saleId) {
      await doBluetooth(saleId);
    },

    // Modal ichidagi tugmalar uchun
    doPrint,
    doPdf,
    doShare,
    async doRawBT(saleId) { await doRawBT(saleId); },
    async doBluetooth(saleId) { await doBluetooth(saleId); },
    _onTitleClick: _onTitleClickForDebug,
    closeModal,
  };

})();

// ── Bluetooth qo'llab-quvvatlash tekshiruvi ──────────────────────────────────
window.isBluetoothSupported = () => !!navigator.bluetooth;