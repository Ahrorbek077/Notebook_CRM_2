# notebook/sms/services.py
"""
Eskiz.uz orqali SMS yuborish.

Sozlash (.env):
    ESKIZ_EMAIL=...           — eskiz.uz kabinetingizdagi email
    ESKIZ_PASSWORD=...        — eskiz.uz kabinetidan olingan SMS PAROLI
                                 (oddiy parol emas — kabinet > SMS biriktirilgan parol)
    ESKIZ_FROM=4546           — tasdiqlangan "sender name"ingiz bo'lsa uni yozing,
                                 bo'lmasa standart umumiy raqam 4546 qoladi

Token Eskiz tomonidan ~30 kunga beriladi — biz Redis cache'da saqlaymiz va
muddati tugaganda (yoki 401 kelganda) avtomatik qayta olamiz.
"""
import logging
from decimal import Decimal

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

ESKIZ_BASE_URL  = getattr(settings, 'ESKIZ_BASE_URL', 'https://notify.eskiz.uz/api')
TOKEN_CACHE_KEY = 'eskiz_sms_token'
TOKEN_CACHE_TTL = 25 * 24 * 60 * 60  # 25 kun (token 30 kunga berilgani uchun ehtiyot zaxirasi bilan)


class EskizAPIError(Exception):
    pass


class SmsRateLimitError(Exception):
    """Shu mijozga juda tez-tez SMS yuborishga urinilganda ko'tariladi."""
    pass


class EskizClient:

    @staticmethod
    def _login() -> str:
        email    = settings.ESKIZ_EMAIL
        password = settings.ESKIZ_PASSWORD
        if not email or not password:
            raise EskizAPIError("ESKIZ_EMAIL / ESKIZ_PASSWORD sozlanmagan (.env fayliga qarang)")

        resp = requests.post(
            f"{ESKIZ_BASE_URL}/auth/login",
            data={'email': email, 'password': password},
            timeout=10,
        )
        if resp.status_code != 200:
            raise EskizAPIError(f"Eskiz login xato: {resp.status_code} {resp.text[:200]}")

        data  = resp.json()
        token = data.get('data', {}).get('token')
        if not token:
            raise EskizAPIError(f"Eskiz javobida token topilmadi: {data}")

        cache.set(TOKEN_CACHE_KEY, token, TOKEN_CACHE_TTL)
        return token

    @classmethod
    def _get_token(cls, force_refresh=False) -> str:
        if not force_refresh:
            token = cache.get(TOKEN_CACHE_KEY)
            if token:
                return token
        return cls._login()

    @staticmethod
    def _normalize_phone(phone: str) -> str:
        """+998901234567 / 90 123 45 67 / 998901234567 → 998901234567"""
        digits = ''.join(ch for ch in phone if ch.isdigit())
        if len(digits) == 9:               # 901234567
            digits = '998' + digits
        elif len(digits) == 12 and digits.startswith('998'):
            pass
        return digits

    @classmethod
    def send_sms(cls, phone: str, message: str) -> dict:
        """SMS yuboradi. Muvaffaqiyatli bo'lsa Eskiz javobini (dict) qaytaradi.

        Xato bo'lsa EskizAPIError ko'taradi — chaqiruvchi tomon ushlab,
        SmsLog'ga yozib qo'yadi.
        """
        phone_normalized = cls._normalize_phone(phone)
        if len(phone_normalized) != 12:
            raise EskizAPIError(f"Telefon raqami noto'g'ri formatda: {phone}")

        from_id = getattr(settings, 'ESKIZ_FROM', '4546') or '4546'
        token   = cls._get_token()

        def _do_request(tok):
            return requests.post(
                f"{ESKIZ_BASE_URL}/message/sms/send",
                headers={'Authorization': f'Bearer {tok}'},
                data={
                    'mobile_phone': phone_normalized,
                    'message':      message,
                    'from':         from_id,
                },
                timeout=10,
            )

        resp = _do_request(token)
        if resp.status_code == 401:
            # Token muddati o'tgan — bir marta yangilab qayta urinamiz
            token = cls._get_token(force_refresh=True)
            resp  = _do_request(token)

        if resp.status_code not in (200, 201):
            raise EskizAPIError(f"Eskiz xato: {resp.status_code} {resp.text[:300]}")

        data = resp.json()
        if str(data.get('status', '')).lower() not in ('waiting', 'success', 'ok'):
            raise EskizAPIError(f"Eskiz kutilmagan javob: {data}")

        return data


class SmsService:

    DEBT_TEMPLATE     = ("Hurmatli {name}, sizning qarzingiz {amount} so'm. "
                         "Iltimos, imkon qadar tezroq to'lovni amalga oshiring. Rahmat!")
    ADVANCE_TEMPLATE  = ("Hurmatli {name}, sizning avansingiz {amount} so'm. "
                         "Keyingi xaridingizda hisobga olinadi. Rahmat!")

    RATE_LIMIT_SECONDS = 120  # bitta mijozga ketma-ket SMS orasidagi minimal interval

    @classmethod
    def build_balance_message(cls, client) -> str:
        if client.total_debt > 0:
            return cls.DEBT_TEMPLATE.format(
                name=client.name, amount=f"{client.total_debt:,.0f}".replace(',', ' ')
            )
        return cls.ADVANCE_TEMPLATE.format(
            name=client.name, amount=f"{client.advance_balance:,.0f}".replace(',', ' ')
        )

    @classmethod
    def _rate_limit_key(cls, client) -> str:
        return f'sms_rate_limit_client_{client.id}'

    @classmethod
    def send_balance_sms(cls, client, user=None):
        """Mijozning qarzi/avansi haqida avtomatik SMS yuboradi va SmsLog yaratadi.

        Rate-limit: shu mijozga oxirgi RATE_LIMIT_SECONDS ichida SMS yuborilgan
        bo'lsa, qayta yubormaydi — operator tugmani ketma-ket bossa ham
        haqiqiy SMS faqat bir marta ketadi (pul sarfini oldini olish).
        """
        from django.core.cache import cache
        from .models import SmsLog

        if client.total_debt <= 0 and client.advance_balance <= 0:
            raise ValueError("Mijozning qarzi yoki avansi yo'q — SMS yuborishga hojat yo'q")
        if not client.phone:
            raise ValueError("Mijozning telefon raqami kiritilmagan")

        rate_key = cls._rate_limit_key(client)
        if cache.get(rate_key):
            raise SmsRateLimitError(
                f"Bu mijozga {cls.RATE_LIMIT_SECONDS} soniya ichida SMS yuborilgan. "
                f"Iltimos, biroz kuting va qayta urinib ko'ring."
            )
        # ── Avval cache'ga belgilab qo'yamiz — bir vaqtda 2 ta so'rov kelsa ham
        # (masalan ikki marta tez-tez bosilsa) faqat biri SMS yubora oladi.
        cache.set(rate_key, True, cls.RATE_LIMIT_SECONDS)

        message = cls.build_balance_message(client)
        log = SmsLog.objects.create(
            business=client.business, client=client, phone=client.phone,
            message=message, status=SmsLog.STATUS_PENDING, sent_by=user,
        )
        try:
            result = EskizClient.send_sms(client.phone, message)
            log.status   = SmsLog.STATUS_SENT
            log.eskiz_id = str(result.get('id', ''))
            log.save(update_fields=['status', 'eskiz_id'])
        except Exception as e:
            log.status = SmsLog.STATUS_FAILED
            log.error  = str(e)[:255]
            log.save(update_fields=['status', 'error'])
            # ── Xato bo'lsa rate-limit'ni olib tashlaymiz — operator real
            # xatodan keyin (masalan tarmoq xatosi) darhol qayta urinishi mumkin.
            cache.delete(rate_key)
            raise
        return log