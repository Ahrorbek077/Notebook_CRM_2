# notebook/core/utils.py
"""
Barcha app'lar foydalanadigan utility funksiyalar.
"""
import uuid
from django.utils.text import slugify


# ── Kirill → Lotin transliteratsiya jadvali ──────────────────────────────────
_CYR_TO_LAT = {
    # Rus Kirill
    'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'yo',
    'ж':'zh','з':'z','и':'i','й':'y','к':'k','л':'l','м':'m',
    'н':'n','о':'o','п':'p','р':'r','с':'s','т':'t','у':'u',
    'ф':'f','х':'x','ц':'ts','ч':'ch','ш':'sh','щ':'sch',
    'ъ':'','ы':'y','ь':'','э':'e','ю':'yu','я':'ya',
    # O'zbek Kirill (maxsus harflar)
    'ғ':'gh','қ':'q','ҳ':'h','ў':'o','ӯ':'u',
    # Katta harflar avtomatik lower() orqali hal bo'ladi
}


def smart_slug(text: str) -> str:
    """
    Har qanday tilda yozilgan matndan xavfsiz slug yaratadi.

    1. Kirill → Lotin transliteratsiya
    2. Django slugify (ASCII)
    3. Bo'sh bo'lsa → unicode slugify
    4. Hali bo'sh → uuid fragment

    Misol:
        'Компьютер стол'  → 'kompyuter-stol'
        'Samsung телефон' → 'samsung-telefon'
        'O'zbek mahsulot' → 'ozbek-mahsulot'
        'Ўзбек товар'     → 'ozbek-tovar'
        '!!!'             → 'a1b2c3d4'   (uuid fragment)
    """
    if not text or not text.strip():
        return str(uuid.uuid4())[:8]

    # Kirill harflarni lotin ga o'tkazish
    transliterated = ''.join(_CYR_TO_LAT.get(ch, ch) for ch in text.lower())

    # ASCII slugify
    slug = slugify(transliterated)

    # Bo'sh bo'lsa unicode bilan urinib ko'r
    if not slug:
        slug = slugify(text, allow_unicode=True)

    # Hali ham bo'sh bo'lsa — uuid
    if not slug:
        slug = str(uuid.uuid4())[:8]

    return slug
