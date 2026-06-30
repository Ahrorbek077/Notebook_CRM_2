# notebook/clients/services_receipt.py
"""
Chek PDF generatori — SERVERDA ishlaydi (jsPDF emas).

Sabab: mahsulot/mijoz nomlari ko'pincha Kirill alifbosida yoziladi
("БАНАН", "Лола ўтиби каминат" kabi). Brauzer tomonidagi jsPDF
standart shriftlari (Helvetica) faqat lotin harflarini biladi —
shuning uchun Kirill matn PDF'da umuman ko'rinmay, deyarli bo'sh
chek chiqib qolardi.

Bu yerda DejaVu Sans shrifti ishlatiladi — u lotin, kirill va
o'zbekcha (')cha harflarning barchasini to'liq qo'llab-quvvatlaydi.
"""
import os
from io import BytesIO

from django.conf import settings
from reportlab.lib.pagesizes import mm
from reportlab.lib import colors
from reportlab.lib.units import mm as mm_unit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

FONT_DIR = settings.BASE_DIR / 'static' / 'fonts'
_FONTS_REGISTERED = False


def _ensure_fonts():
    """DejaVu Sans shriftini bir martagina ro'yxatdan o'tkazadi."""
    global _FONTS_REGISTERED
    if _FONTS_REGISTERED:
        return
    pdfmetrics.registerFont(TTFont('DejaVuSans', str(FONT_DIR / 'DejaVuSans.ttf')))
    pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', str(FONT_DIR / 'DejaVuSans-Bold.ttf')))
    _FONTS_REGISTERED = True


def _fmt_money(n) -> str:
    return f"{n:,.0f}".replace(',', ' ') + " so'm"


def _fmt_qty(val) -> str:
    n = float(val)
    if n == int(n):
        return str(int(n))
    return f"{n:.3f}".rstrip('0').rstrip('.')


def build_receipt_pdf(sale) -> bytes:
    """Berilgan Sale obyekti uchun 58mm kvitansiya (chek) PDF baytlarini qaytaradi.

    58mm — chunki ko'pchilik arzon termo-printerlar (xitoylik label printer)
    aynan shu kenglikda qog'oz ishlatadi. Agar 80mm'da yasab 58mm'ga
    "siqilsa" — matn xira/kichik chiqib qoladi, shuning uchun to'g'ridan-to'g'ri
    58mm'ning o'zida, yetarlicha katta shrift bilan chiqaramiz.

    Maxfiylik: mijozning ismi va qarz/avans summasi CHEKDA ko'rsatilmaydi
    (faqat telefon raqami) — chunki ba'zi mijozlar tizimda taxallus/
    laqab bilan kiritilgan bo'lishi mumkin, bu mijozni xafa qilmasligi uchun.
    """
    _ensure_fonts()

    width = 80 * mm_unit
    items = list(sale.items.all())
    base_h     = 46 * mm_unit
    per_item_h = 10 * mm_unit
    height = base_h + per_item_h * max(len(items), 1)

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(width, height))

    LM = 3 * mm_unit          # left margin
    RM = width - 3 * mm_unit  # right edge
    y  = height - 7 * mm_unit

    business_name = sale.business.name if sale.business else 'Do\u02bckon'

    def line(yy):
        c.setStrokeColor(colors.HexColor('#999999'))
        c.setLineWidth(0.3)
        c.line(LM, yy, RM, yy)

    def text(x, yy, s, font='DejaVuSans', size=9, align='left', color='#000000'):
        c.setFont(font, size)
        c.setFillColor(colors.HexColor(color))
        if align == 'right':
            c.drawRightString(x, yy, s)
        elif align == 'center':
            c.drawCentredString(x, yy, s)
        else:
            c.drawString(x, yy, s)

    # ── Sarlavha (biznes nomi) ───────────────────────────────────────────
    text(width / 2, y, business_name, font='DejaVuSans-Bold', size=14, align='center', color='#0d9bb5')
    y -= 5.5 * mm_unit
    text(width / 2, y, f"Sotuv cheki #{sale.id}", size=8.5, align='center', color='#666666')
    y -= 3 * mm_unit
    line(y); y -= 5 * mm_unit

    # ── Telefon va sana (ism/qarz ko'rsatilmaydi — maxfiylik) ────────────
    rows = [
        ('Telefon', sale.client.phone or '—'),
        ('Kassir', sale.user.get_full_name() if sale.user else '—'),
        ('Sana', sale.created_at.strftime('%d.%m.%Y %H:%M')),
    ]
    for label, value in rows:
        text(LM, y, label, size=8, color='#777777')
        text(RM, y, str(value), size=8, align='right', color='#111111')
        y -= 4.6 * mm_unit

    line(y); y -= 4.5 * mm_unit

    # ── Ustun sarlavhasi ──────────────────────────────────────────────────
    text(LM, y, 'Mahsulot', font='DejaVuSans-Bold', size=8)
    text(RM, y, 'Jami', font='DejaVuSans-Bold', size=8, align='right')
    y -= 3.2 * mm_unit
    line(y); y -= 4.5 * mm_unit

    # ── Mahsulotlar ──────────────────────────────────────────────────────
    GAP = 2 * mm_unit  # nom va narx orasidagi minimal bo'shliq
    for item in items:
        name = item.product.name
        subtotal = item.price_at_sale * item.quantity
        price_str = _fmt_money(subtotal)
        price_w = pdfmetrics.stringWidth(price_str, 'DejaVuSans', 9)
        max_name_w = (RM - LM) - price_w - GAP

        # Nom narx bilan to'qnashmasligi uchun haqiqiy piksel kengligiga qarab qisqartiramiz
        while pdfmetrics.stringWidth(name, 'DejaVuSans', 9) > max_name_w and len(name) > 3:
            name = name[:-1]
        if name != item.product.name:
            name = name[:-2] + '..'

        text(LM, y, name, size=9)
        text(RM, y, price_str, size=9, align='right', color='#b8860b')
        y -= 4.2 * mm_unit
        qty_line = f"  {_fmt_qty(item.quantity)} {item.product.get_unit_type_display()} x {_fmt_money(item.price_at_sale)}"
        text(LM, y, qty_line, size=7, color='#888888')
        y -= 4.8 * mm_unit

    line(y); y -= 5.5 * mm_unit

    # ── Jami ──────────────────────────────────────────────────────────────
    text(LM, y, 'JAMI', font='DejaVuSans-Bold', size=11)
    text(RM, y, _fmt_money(sale.total_amount), font='DejaVuSans-Bold', size=11, align='right', color='#0d9bb5')
    y -= 6 * mm_unit

    line(y); y -= 5.5 * mm_unit
    text(width / 2, y, f"Xarid uchun rahmat! \u00b7 {business_name}", size=7, align='center', color='#999999')

    c.showPage()
    c.save()
    return buf.getvalue()


def build_receipt_png(sale) -> bytes:
    """Chekni PNG RASM sifatida yaratadi — QORA-OQ (1-bit), RANGSIZ.

    Sabab: ko'plab "label printer" mobil ilovalari (masalan Eleph Label,
    Phomemo, va shunga o'xshashlar) shunday qurilmalar (termal yorliq
    printerlari) uchun mo'ljallangan — ular faqat ODDIY OQ-QORA rasmlarni
    to'g'ri qabul qiladi. Avval rangli (ko'k/sariq) rasm yuborilganda
    ilova uni "tushunmay" oq/bo'sh ko'rsatardi. Bu — termal printerlarning
    o'zi ham faqat bitta rangda (qora) bosib chiqarganligi uchun ham
    mantiqan to'g'ri — rang baribir qog'ozda ko'rinmaydi.
    """
    from PIL import Image, ImageDraw, ImageFont

    _ensure_fonts()

    DPI    = 300
    MM2PX  = DPI / 25.4
    width  = int(80 * MM2PX)

    items = list(sale.items.all())
    base_h     = int(90 * MM2PX)  # sarlavha+info+ustun+jami+footer (mahsulotlarsiz)
    per_item_h = int(13 * MM2PX)  # har bir mahsulot uchun (nomi + soni/narxi qatori)
    height = base_h + per_item_h * max(len(items), 1)

    img = Image.new('L', (width, height), 255)  # 'L' = 8-bit grayscale, 255=oq
    draw = ImageDraw.Draw(img)

    def font(size, bold=False):
        path = FONT_DIR / ('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf')
        return ImageFont.truetype(str(path), int(size * MM2PX / 2.5))

    LM = int(3 * MM2PX)
    RM = width - int(3 * MM2PX)
    y  = int(7 * MM2PX)

    business_name = sale.business.name if sale.business else 'Do\u02bckon'

    def text(x, y, s, size=9, bold=False, align='left'):
        f = font(size, bold)
        bbox = draw.textbbox((0, 0), s, font=f)
        w = bbox[2] - bbox[0]
        if align == 'right':
            x = x - w
        elif align == 'center':
            x = x - w / 2
        draw.text((x, y), s, font=f, fill=0)  # 0 = qora
        return bbox[3] - bbox[1]

    def line(yy):
        draw.line([(LM, yy), (RM, yy)], fill=0, width=1)

    # ── Sarlavha ──────────────────────────────────────────────────────────
    text(width / 2, y, business_name, size=14, bold=True, align='center')
    y += int(7 * MM2PX)
    text(width / 2, y, f"Sotuv cheki #{sale.id}", size=8.5, align='center')
    y += int(6 * MM2PX)
    line(y); y += int(5 * MM2PX)

    # ── Telefon va sana (ism/qarz ko'rsatilmaydi — maxfiylik) ────────────
    rows = [
        ('Telefon', sale.client.phone or '\u2014'),
        ('Kassir', sale.user.get_full_name() if sale.user else '\u2014'),
        ('Sana', sale.created_at.strftime('%d.%m.%Y %H:%M')),
    ]
    for label, value in rows:
        text(LM, y, label, size=8)
        text(RM, y, str(value), size=8, align='right')
        y += int(6 * MM2PX)

    line(y); y += int(5 * MM2PX)

    # ── Ustun sarlavhasi ──────────────────────────────────────────────────
    text(LM, y, 'Mahsulot', size=8, bold=True)
    text(RM, y, 'Jami', size=8, bold=True, align='right')
    y += int(5 * MM2PX)
    line(y); y += int(5 * MM2PX)

    # ── Mahsulotlar ──────────────────────────────────────────────────────
    GAP = int(2 * MM2PX)  # nom va narx orasidagi minimal bo'shliq
    for item in items:
        name = item.product.name
        subtotal = item.price_at_sale * item.quantity
        price_str = _fmt_money(subtotal)

        f_name  = font(9)
        f_price = font(9, bold=True)
        price_w = draw.textbbox((0, 0), price_str, font=f_price)[2]
        max_name_w = (RM - LM) - price_w - GAP

        # Nom narx bilan to'qnashmasligi uchun piksel kengligiga qarab qisqartiramiz
        while draw.textbbox((0, 0), name, font=f_name)[2] > max_name_w and len(name) > 3:
            name = name[:-1]
        if name != item.product.name:
            name = name[:-2] + '..'

        text(LM, y, name, size=9)
        text(RM, y, price_str, size=9, bold=True, align='right')
        y += int(5.5 * MM2PX)
        qty_line = f"  {_fmt_qty(item.quantity)} {item.product.get_unit_type_display()} x {_fmt_money(item.price_at_sale)}"
        text(LM, y, qty_line, size=7)
        y += int(5.5 * MM2PX)

    line(y); y += int(7 * MM2PX)

    # ── Jami ──────────────────────────────────────────────────────────────
    text(LM, y, 'JAMI', size=11, bold=True)
    text(RM, y, _fmt_money(sale.total_amount), size=11, bold=True, align='right')
    y += int(8 * MM2PX)

    line(y); y += int(6 * MM2PX)
    text(width / 2, y, f"Xarid uchun rahmat! \u00b7 {business_name}", size=7, align='center')
    y += int(6 * MM2PX)

    img = img.crop((0, 0, width, min(y, height)))

    buf = BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()
