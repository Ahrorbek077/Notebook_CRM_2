# notebook/sms/models.py
from django.conf import settings
from django.db import models


class SmsLog(models.Model):
    """Yuborilgan har bir SMS ning tarixi — audit va xatolarni kuzatish uchun."""

    STATUS_PENDING = 'pending'
    STATUS_SENT    = 'sent'
    STATUS_FAILED  = 'failed'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Yuborilmoqda'),
        (STATUS_SENT,    'Yuborildi'),
        (STATUS_FAILED,  'Xato'),
    ]

    business    = models.ForeignKey(
        'business.Business', on_delete=models.CASCADE,
        related_name='sms_logs', null=True, blank=True, verbose_name="Biznes"
    )
    client      = models.ForeignKey(
        'clients.Client', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='sms_logs', verbose_name="Mijoz"
    )
    phone       = models.CharField(max_length=20, verbose_name="Telefon")
    message     = models.TextField(verbose_name="Matn")
    status      = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    eskiz_id    = models.CharField(max_length=64, blank=True, verbose_name="Eskiz ID")
    error       = models.CharField(max_length=255, blank=True, verbose_name="Xato matni")
    sent_by     = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='sms_logs'
    )
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "SMS tarixi"
        verbose_name_plural = "SMS tarixi"

    def __str__(self):
        return f"{self.phone} — {self.get_status_display()} ({self.created_at:%d.%m.%Y %H:%M})"
