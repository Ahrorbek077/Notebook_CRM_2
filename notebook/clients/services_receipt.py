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
    """Berilgan Sale obyekti uchun 80mm kvitansiya (chek) PDF baytlarini qaytaradi."""
    _ensure_fonts()

    width = 80 * mm_unit
    # Balandlikni mahsulotlar soniga qarab dinamik hisoblaymiz
    items = list(sale.items.all())
    base_h  = 60 * mm_unit
    per_item_h = 9 * mm_unit
    height = base_h + per_item_h * max(len(items), 1)

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(width, height))

    LM = 4 * mm_unit          # left margin
    RM = width - 4 * mm_unit  # right edge
    y  = height - 8 * mm_unit

    def line(yy):
        c.setStrokeColor(colors.HexColor('#999999'))
        c.setLineWidth(0.3)
        c.line(LM, yy, RM, yy)

    def text(x, yy, s, font='DejaVuSans', size=8, align='left', color='#000000'):
        c.setFont(font, size)
        c.setFillColor(colors.HexColor(color))
        if align == 'right':
            c.drawRightString(x, yy, s)
        elif align == 'center':
            c.drawCentredString(x, yy, s)
        else:
            c.drawString(x, yy, s)

    # ── Sarlavha ──────────────────────────────────────────────────────────
    text(width / 2, y, 'NoteBook', font='DejaVuSans-Bold', size=13, align='center', color='#0d9bb5')
    y -= 5 * mm_unit
    text(width / 2, y, f"Sotuv cheki #{sale.id}", size=8, align='center', color='#666666')
    y -= 3 * mm_unit
    line(y); y -= 5 * mm_unit

    # ── Mijoz/kassir ma'lumotlari ─────────────────────────────────────────
    rows = [
        ('Mijoz', sale.client.name),
        ('Telefon', sale.client.phone or '—'),
        ('Kassir', sale.user.get_full_name() if sale.user else '—'),
        ('Sana', sale.created_at.strftime('%d.%m.%Y %H:%M')),
    ]
    for label, value in rows:
        text(LM, y, label, size=7.5, color='#777777')
        text(RM, y, str(value), size=7.5, align='right', color='#111111')
        y -= 4.2 * mm_unit

    line(y); y -= 4.5 * mm_unit

    # ── Ustun sarlavhasi ──────────────────────────────────────────────────
    text(LM, y, 'Mahsulot', font='DejaVuSans-Bold', size=7)
    text(RM, y, 'Jami', font='DejaVuSans-Bold', size=7, align='right')
    y -= 3 * mm_unit
    line(y); y -= 4 * mm_unit

    # ── Mahsulotlar ──────────────────────────────────────────────────────
    for item in items:
        name = item.product.name
        if len(name) > 30:
            name = name[:28] + '..'
        subtotal = item.price_at_sale * item.quantity
        text(LM, y, name, size=8)
        text(RM, y, _fmt_money(subtotal), size=8, align='right', color='#b8860b')
        y -= 3.8 * mm_unit
        qty_line = f"  {_fmt_qty(item.quantity)} {item.product.get_unit_type_display()} x {_fmt_money(item.price_at_sale)}"
        text(LM, y, qty_line, size=6.5, color='#888888')
        y -= 4.2 * mm_unit

    line(y); y -= 5 * mm_unit

    # ── Jami ──────────────────────────────────────────────────────────────
    text(LM, y, 'JAMI', font='DejaVuSans-Bold', size=9.5)
    text(RM, y, _fmt_money(sale.total_amount), font='DejaVuSans-Bold', size=9.5, align='right', color='#0d9bb5')
    y -= 5 * mm_unit

    if sale.client.total_debt > 0:
        text(LM, y, 'Qarz', size=8, color='#d32f2f')
        text(RM, y, _fmt_money(sale.client.total_debt), size=8, align='right', color='#d32f2f')
        y -= 4.5 * mm_unit
    elif sale.client.advance_balance > 0:
        text(LM, y, 'Avans', size=8, color='#2e7d32')
        text(RM, y, _fmt_money(sale.client.advance_balance), size=8, align='right', color='#2e7d32')
        y -= 4.5 * mm_unit

    line(y); y -= 5 * mm_unit
    text(width / 2, y, 'Xarid uchun rahmat! · NoteBook', size=6.5, align='center', color='#999999')

    c.showPage()
    c.save()
    return buf.getvalue()
