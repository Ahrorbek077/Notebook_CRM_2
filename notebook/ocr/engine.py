# notebook/ocr/engine.py
"""
Tesseract OCR dvigateli — chek rasmidan matn o'qish. AI/API ISHLATILMAYDI,
hammasi lokal va bepul ishlaydi.

O'RNATISH (serverda bir marta):
    sudo apt install tesseract-ocr tesseract-ocr-uzb-cyrl tesseract-ocr-rus
    pip install pytesseract

Windows'da: https://github.com/UB-Mannheim/tesseract/wiki dan o'rnatib,
"Additional language data" da Uzbek-Cyrillic va Russian ni belgilang.

Termochek OCR sifati RASMGA juda bog'liq, shuning uchun o'qishdan oldin
rasmni tayyorlaymiz (preprocessing): kulrang → kattalashtirish → kontrast
→ oq-qora (threshold). Bu aniqlikni sezilarli oshiradi.
"""
import logging
import shutil

from PIL import Image, ImageOps, ImageFilter

logger = logging.getLogger(__name__)

# Kirill chek uchun til to'plami. uzb_cyrl bo'lmasa rus ham kirillni o'qiydi.
LANG_PREFERRED = 'uzb_cyrl+rus+eng'
LANG_FALLBACK  = 'rus+eng'

MAX_SIDE = 2200   # juda katta rasmlarni kichraytirish (tezlik uchun)
MIN_SIDE = 1000   # juda kichik rasmlarni kattalashtirish (aniqlik uchun)


class OcrError(Exception):
    pass


def _check_tesseract():
    if shutil.which('tesseract') is None:
        raise OcrError(
            "Tesseract o'rnatilmagan. Server'da bajaring: "
            "sudo apt install tesseract-ocr tesseract-ocr-uzb-cyrl tesseract-ocr-rus"
        )


def _available_lang() -> str:
    """uzb_cyrl o'rnatilganmi tekshiradi, bo'lmasa rus'ga tushadi."""
    import pytesseract
    try:
        langs = set(pytesseract.get_languages(config=''))
    except Exception:
        return LANG_FALLBACK
    if 'uzb_cyrl' in langs:
        return LANG_PREFERRED if 'rus' in langs else 'uzb_cyrl+eng'
    if 'rus' in langs:
        logger.warning("OCR: uzb_cyrl topilmadi, rus bilan o'qilmoqda "
                       "(o'rnatish tavsiya: tesseract-ocr-uzb-cyrl)")
        return LANG_FALLBACK
    raise OcrError(
        "Kirill tili o'rnatilmagan. Bajaring: "
        "sudo apt install tesseract-ocr-uzb-cyrl tesseract-ocr-rus"
    )


def preprocess(img: Image.Image) -> Image.Image:
    """Termochek rasmini OCR uchun tayyorlash."""
    # EXIF bo'yicha to'g'rilash (telefon rasmlari yonboshlagan bo'ladi)
    img = ImageOps.exif_transpose(img)

    # Kulrang
    img = img.convert('L')

    # O'lcham normalizatsiyasi
    w, h = img.size
    long_side = max(w, h)
    if long_side > MAX_SIDE:
        scale = MAX_SIDE / long_side
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    elif long_side < MIN_SIDE:
        scale = MIN_SIDE / long_side
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    # Kontrastni cho'zish + yengil shovqin tozalash
    img = ImageOps.autocontrast(img, cutoff=2)
    img = img.filter(ImageFilter.MedianFilter(size=3))

    # Yengil binarizatsiya (juda qattiq threshold ingichka harflarni yeb yuboradi,
    # shuning uchun yumshoq nuqta tanlangan)
    img = img.point(lambda p: 255 if p > 150 else 0)

    return img


def image_to_text(file_obj) -> str:
    """
    Yuklangan rasm (Django UploadedFile yoki fayl obyekti) → OCR matn.
    Xatoda OcrError ko'taradi (foydalanuvchiga ko'rsatiladigan xabar bilan).
    """
    _check_tesseract()
    import pytesseract

    try:
        img = Image.open(file_obj)
    except Exception:
        raise OcrError("Rasm o'qib bo'lmadi. JPG yoki PNG yuboring.")

    img  = preprocess(img)
    lang = _available_lang()

    try:
        # PSM 6 — "bir tekis matn bloki": chek uchun eng mos rejim
        text = pytesseract.image_to_string(img, lang=lang, config='--psm 6')
    except Exception as e:
        logger.exception("Tesseract xatosi")
        raise OcrError(f"OCR xatosi: {e}")

    text = (text or '').strip()
    if len(text) < 5:
        raise OcrError(
            "Matn o'qilmadi. Rasmni yaxshi yorug'likda, tekis va yaqinroq olib qayta urining."
        )
    logger.info("OCR: %s belgi o'qildi (lang=%s)", len(text), lang)
    return text
