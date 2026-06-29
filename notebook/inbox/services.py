# notebook/inbox/services.py
import re
from decimal import Decimal, InvalidOperation

# Summaga yaqin so'zlar — shu so'zlar yonidagi raqamga ko'proq ishonamiz
_AMOUNT_HINTS  = re.compile(r"(so['\u2019]?m|som|сум|uzs|tush|kelib|qabul|popolnenie|received|credit|zachislen)", re.IGNORECASE)
# Bu so'zlar yonidagi raqam — balans/qoldiq, TUSHUM emas, shuning uchun chetlab o'tamiz
_BALANCE_HINTS = re.compile(r"(balans|balance|qoldiq|остаток|dostup)", re.IGNORECASE)

_NUMBER_RE = re.compile(r"\d{1,3}(?:[ .,]\d{3})+(?:[.,]\d{1,2})?|\d{4,}(?:[.,]\d{1,2})?")


def _normalize_number(raw: str) -> Decimal | None:
    """'150 000', '150,000.00', '150.000,00' kabi formatlarni Decimal'ga aylantiradi."""
    s = raw.strip()
    # Oxirgi vergul/nuqtadan keyin aniq 1-2 ta raqam bo'lsa — bu kasr qismi
    m = re.search(r"[.,](\d{1,2})$", s)
    decimal_part = None
    if m and len(m.group(1)) <= 2:
        decimal_part = m.group(1)
        s = s[:m.start()]
    integer_part = re.sub(r"[ .,]", "", s)
    if not integer_part.isdigit():
        return None
    try:
        value = Decimal(integer_part)
        if decimal_part:
            value += Decimal(decimal_part) / Decimal(10 ** len(decimal_part))
        return value
    except InvalidOperation:
        return None


def extract_amount(text: str) -> Decimal | None:
    """SMS/bildirishnoma matnidan eng ehtimoliy tushum summasini taxmin qiladi.

    Bu — TAXMINIY natija. Foydalanuvchi "Kelgan to'lovlar" sahifasida
    tasdiqlashdan oldin tahrirlashi mumkin, shuning uchun 100% aniqlik
    shart emas — eng yaxshi taxminni berish kifoya.
    """
    candidates = []
    for m in _NUMBER_RE.finditer(text):
        value = _normalize_number(m.group())
        if value is None or value <= 0:
            continue

        # Karta raqami qoldig'i (masalan "*4521") — summa emas, chetlab o'tamiz
        if text[max(0, m.start() - 2): m.start()].find('*') != -1:
            continue

        before = text[max(0, m.start() - 18): m.start()]
        after  = text[m.end(): m.end() + 18]

        score = 0
        if _AMOUNT_HINTS.search(after) or _AMOUNT_HINTS.search(before):
            score += 10
        # "Balans/qoldiq" deyarli har doim summadan OLDIN keladi (masalan
        # "Balans: 1 250 000") — shuning uchun faqat oldingi matnda tekshiramiz,
        # aks holda qo'shni (haqiqiy) summaning "keyingi" oynasiga tushib qolib,
        # noto'g'ri jazolanishi mumkin.
        if _BALANCE_HINTS.search(before):
            score -= 20

        candidates.append((score, value, m.start()))

    if not candidates:
        return None

    # Eng yuqori "score"ga ega, teng bo'lsa kattaroq summani tanlaymiz
    candidates.sort(key=lambda c: (c[0], c[1]), reverse=True)
    return candidates[0][1]


def extract_sender_hint(text: str) -> str:
    """Jo'natuvchi ismi/karta raqami bo'lagini (agar topilsa) ajratib oladi — faqat
    operatorga vizual yordam uchun, avtomatik bog'lashda ishlatilmaydi."""
    m = re.search(r"\*\d{4}\b", text)  # masalan *1234 (karta oxiri)
    return m.group() if m else ""


class IncomingTransactionService:

    @staticmethod
    def create_from_webhook(business, raw_text: str, source='sms') -> "IncomingTransaction":
        from .models import IncomingTransaction
        return IncomingTransaction.objects.create(
            business=business,
            raw_text=raw_text[:4000],
            parsed_amount=extract_amount(raw_text),
            sender_hint=extract_sender_hint(raw_text),
            source=source,
        )

    @staticmethod
    def match_to_client(transaction, client, amount, user=None):
        """Tasdiqlash — haqiqiy Payment yaratadi va transactionni "matched" qiladi."""
        from django.utils import timezone
        from notebook.payments.services import PaymentService
        from .models import IncomingTransaction

        if transaction.status == IncomingTransaction.STATUS_MATCHED:
            raise ValueError("Bu yozuv allaqachon bog'langan")

        payment = PaymentService.create_payment(
            client=client, amount=amount, user=user,
            note=f"Avtomatik aniqlangan (bank xabari) — #{transaction.id}",
        )
        transaction.matched_client  = client
        transaction.matched_payment = payment
        transaction.matched_by      = user
        transaction.matched_at      = timezone.now()
        transaction.status          = IncomingTransaction.STATUS_MATCHED
        transaction.save(update_fields=[
            'matched_client', 'matched_payment', 'matched_by', 'matched_at', 'status'
        ])
        return payment


def IncomingTransactionService_STATUS_MATCHED():
    from .models import IncomingTransaction
    return IncomingTransaction.STATUS_MATCHED
