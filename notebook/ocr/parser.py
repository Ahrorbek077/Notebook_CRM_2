# notebook/ocr/parser.py
"""
OCR matnini qatorlarga ajratib, mahsulot + miqdor + narxni topish va
filial mahsulotlariga MOSLASHTIRISH (matching).

Chek kirillda, katalogdagi mahsulot nomlari lotinda bo'lishi mumkin —
shuning uchun taqqoslashdan oldin ikkalasi ham lotinga o'girilib,
difflib bilan o'xshashlik hisoblanadi.

Parser 100% aniq bo'lishi SHART EMAS — natija baribir foydalanuvchiga
tahrirlanadigan jadvalda ko'rsatiladi va u tasdiqlaydi. Parserning vazifasi
imkon qadar ko'p qatorni to'g'ri "taxmin" qilib berish.
"""
import re
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher

# ── Kirill → Lotin (taqqoslash uchun) ────────────────────────────────────────
CYR_TO_LAT = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
    'ж': 'j', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
    'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
    'ф': 'f', 'х': 'x', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sh',
    'ъ': '', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
    'ў': 'o', 'қ': 'q', 'ғ': 'g', 'ҳ': 'h',
}


def normalize(text: str) -> str:
    """Taqqoslash uchun: kirill→lotin, kichik harf, ortiqcha belgilar tashlanadi."""
    out = []
    for ch in text.lower():
        out.append(CYR_TO_LAT.get(ch, ch))
    s = ''.join(out)
    s = s.replace("'", "").replace("`", "").replace("ʼ", "")
    s = re.sub(r'[^a-z0-9 ]+', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def similarity(a: str, b: str) -> float:
    """0..1 o'xshashlik. Qisman moslik ham hisobga olinadi (nom ichida bo'lsa)."""
    na, nb = normalize(a), normalize(b)
    if not na or not nb:
        return 0.0
    ratio = SequenceMatcher(None, na, nb).ratio()
    # Biri ikkinchisining ichida bo'lsa — kuchli signal
    if na in nb or nb in na:
        ratio = max(ratio, 0.82)
    return ratio


# ── Raqam yordamchilari ──────────────────────────────────────────────────────
def _to_decimal(s: str):
    """'12 500,00' | '12.500' | '3,5' kabilarni Decimal'ga o'giradi."""
    s = s.strip().replace(' ', '').replace('\u00a0', '')
    if not s:
        return None
    # 12.500,00 yoki 12,500.00 — mingliklarni ajratish
    if ',' in s and '.' in s:
        if s.rfind(',') > s.rfind('.'):
            s = s.replace('.', '').replace(',', '.')
        else:
            s = s.replace(',', '')
    elif ',' in s:
        # '3,5' kasrmi yoki '12,500' minglikmi?
        head, tail = s.rsplit(',', 1)
        s = head.replace(',', '') + ('.' + tail if len(tail) <= 2 else tail)
    try:
        d = Decimal(s)
        return d if d >= 0 else None
    except InvalidOperation:
        return None


NUM   = r'\d[\d\s.,]*'
X_SEP = r'[xхXХ×*]'   # lotin x, kirill х, ko'paytirish belgilari

# "3 x 12500" / "3,5 х 12 500 = 43 750"
QTY_PRICE_RE = re.compile(rf'({NUM})\s*{X_SEP}\s*({NUM})')
# Qator oxiridagi raqamlar (narx/summa ustunlari)
TRAIL_NUMS_RE = re.compile(rf'({NUM})\s*$')
# Chekda mahsulot bo'lmagan xizmat qatorlari (kirill+lotin kalit so'zlar)
SKIP_RE = re.compile(
    r'(жами|итог|итого|всего|чек|касс|сумма|скидка|карта|наличн|терминал|'
    r'jami|chek|kassa|summa|chegirma|karta|naqd|терм|ннм|инн|фиск|штрих|'
    r'кайтим|qaytim|сдача|сана|дата|время|вақт|\bтел\b|телефон|www|http|'
    r'рахмат|rahmat|спасибо|хариди?нгиз|kelganingiz|қайтим)', re.IGNORECASE)


def parse_receipt_text(text: str) -> list:
    """
    OCR matn → [{name, qty, price, raw}] ro'yxati.

    Qo'llab-quvvatlanadigan ko'rinishlar:
      A) "Нон буханка  3 x 4500 = 13500"        (bir qatorda)
      B) "Кока-Кола 1.5л"                        (nom alohida qatorda)
         "2 х 12000   24000"                     (miqdor keyingi qatorda)
      C) "Шакар 1кг   12500"                     (nom + narx, miqdor=1)
    """
    rows = []
    pending_name = None   # B-ko'rinish uchun: oldingi qatordagi nom

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if len(line) < 2:
            continue
        if SKIP_RE.search(line):
            pending_name = None
            continue

        m = QTY_PRICE_RE.search(line)
        if m:
            qty   = _to_decimal(m.group(1))
            price = _to_decimal(m.group(2))
            # "x" dan oldingi matn — nom (bo'lmasa oldingi qatordagi nom)
            name_part = line[:m.start()].strip(' -.:')
            name = name_part if len(name_part) >= 2 else (pending_name or '')
            if qty and price and (name or pending_name):
                rows.append({
                    'name':  name or pending_name,
                    'qty':   str(qty),
                    'price': str(price),
                    'raw':   raw_line.strip(),
                })
                pending_name = None
                continue

        # Raqamsiz qator → nom bo'lishi mumkin, keyingi qatorni kutamiz
        if not re.search(r'\d', line):
            pending_name = line.strip(' -.:')
            continue

        # Nom + oxirida narx ("Шакар 1кг 12500") — miqdor 1 deb olamiz
        m2 = TRAIL_NUMS_RE.search(line)
        if m2:
            price = _to_decimal(m2.group(1))
            name  = line[:m2.start()].strip(' -.:')
            # Narx aql doirasida (100 so'm — 100 mln) va nomda kamida 3 harf bo'lsin
            if (price and Decimal('100') <= price <= Decimal('100000000')
                    and len(re.sub(r'[\d\s.,]', '', name)) >= 3):
                rows.append({
                    'name':  name,
                    'qty':   '1',
                    'price': str(price),
                    'raw':   raw_line.strip(),
                })
                pending_name = None
                continue

        # Hech narsa chiqmadi, LEKIN qatorda yetarli harf bo'lsa — bu nom
        # bo'lishi mumkin (masalan "Кока-Кола 1.5л", "Ун олий нав 2кг" —
        # ichida raqam bor, ammo bu o'lcham, narx emas). Keyingi qatordagi
        # "miqdor x narx" bilan juftlashishi uchun saqlab qo'yamiz.
        letters = re.sub(r'[\d\s.,:;=*xхXХ×%-]', '', line)
        if len(letters) >= 3:
            pending_name = line.strip(' -.:')
        else:
            pending_name = None

    return rows


def match_products(rows: list, products) -> list:
    """
    Har bir parse qilingan qatorga katalogdan ENG O'XSHASH mahsulotni topadi.

    products — Product queryset (filialga tegishli, oldindan filter qilingan).
    Qaytadi: rows + har biriga {product_id, product_name, score} qo'shilgan.
    """
    plist = [(p.id, p.name) for p in products]

    for row in rows:
        best_id, best_name, best_score = None, '', 0.0
        for pid, pname in plist:
            score = similarity(row['name'], pname)
            if score > best_score:
                best_id, best_name, best_score = pid, pname, score
        if best_score >= 0.45:   # past chegara — baribir foydalanuvchi tasdiqlaydi
            row['product_id']   = best_id
            row['product_name'] = best_name
            row['score']        = round(best_score, 2)
        else:
            row['product_id']   = None
            row['product_name'] = ''
            row['score']        = 0.0
    return rows
