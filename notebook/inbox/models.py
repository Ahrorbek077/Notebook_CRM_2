# notebook/inbox/models.py
"""
IncomingTransaction — bank/karta SMS yoki bildirishnomasidan kelgan, hali
hech qaysi mijozga BOG'LANMAGAN pul tushumi.

Oqim:
  1. Telefon (MacroDroid) SMS/bildirishnoma matnini webhook orqali yuboradi.
  2. Shu matn shu yerga "unmatched" holatda yoziladi, summa taxminiy ajratiladi.
  3. Admin/superadmin "Kelgan to'lovlar" sahifasida ko'rib, mijozni tanlaydi.
  4. Tasdiqlangach — haqiqiy Payment yaratiladi, shu yozuv "matched" bo'ladi.

Bu staging-jadval orqali xato mijozga avtomatik yozilib ketish xavfi
oldindan oldi olinadi — har bir tushum INSON tomonidan tasdiqlanadi.
"""
from django.conf import settings
from django.db import models


class IncomingTransaction(models.Model):
    SOURCE_SMS          = 'sms'
    SOURCE_NOTIFICATION  = 'notification'
    SOURCE_MANUAL        = 'manual'
    SOURCE_CHOICES = [
        (SOURCE_SMS,          'SMS'),
        (SOURCE_NOTIFICATION, 'Bildirishnoma'),
        (SOURCE_MANUAL,       "Qo'lda kiritilgan"),
    ]

    STATUS_UNMATCHED = 'unmatched'
    STATUS_MATCHED   = 'matched'
    STATUS_IGNORED   = 'ignored'
    STATUS_CHOICES = [
        (STATUS_UNMATCHED, 'Kutmoqda'),
        (STATUS_MATCHED,   'Bog\u02bclandi'),
        (STATUS_IGNORED,   'E\u02bctibor berilmadi'),
    ]

    business      = models.ForeignKey(
        'business.Business', on_delete=models.CASCADE,
        related_name='incoming_transactions', verbose_name="Biznes"
    )
    raw_text      = models.TextField(verbose_name="Asl matn (SMS/bildirishnoma)")
    parsed_amount = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True,
        verbose_name="Aniqlangan summa (taxminiy)"
    )
    sender_hint   = models.CharField(max_length=120, blank=True, verbose_name="Jo'natuvchi (agar bor bo'lsa)")
    source        = models.CharField(max_length=20, choices=SOURCE_CHOICES, default=SOURCE_SMS)
    status        = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_UNMATCHED)

    matched_client  = models.ForeignKey(
        'clients.Client', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='incoming_transactions', verbose_name="Bog'langan mijoz"
    )
    matched_payment = models.ForeignKey(
        'payments.Payment', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='source_transaction', verbose_name="Yaratilgan to'lov"
    )
    matched_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='matched_transactions'
    )
    matched_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Kelgan to'lov (tasdiqlanmagan)"
        verbose_name_plural = "Kelgan to'lovlar (tasdiqlanmagan)"

    def __str__(self):
        amt = f"{self.parsed_amount:,.0f}" if self.parsed_amount else "?"
        return f"{amt} so'm — {self.get_status_display()} ({self.created_at:%d.%m.%Y %H:%M})"
