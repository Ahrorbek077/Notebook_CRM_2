# notebook/payments/models.py
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone
from notebook.core.managers import NotCancelledManager


class Payment(models.Model):
    client          = models.ForeignKey('clients.Client', on_delete=models.CASCADE, related_name='payments')
    amount          = models.DecimalField(max_digits=12, decimal_places=2)
    user            = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    note            = models.CharField(max_length=255, blank=True)
    refunded_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    created_at      = models.DateTimeField(auto_now_add=True)

    is_cancelled = models.BooleanField(default=False)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='cancelled_payments'
    )

    objects        = models.Manager()
    active_objects = NotCancelledManager()

    class Meta:
        verbose_name = "To'lov"
        verbose_name_plural = "To'lovlar"

    def get_remaining_amount(self):
        return self.amount - self.refunded_amount

    def is_fully_refunded(self):
        return self.refunded_amount >= self.amount

    def cancel(self, cancelled_by=None):
        if self.is_cancelled:
            return
        from django.db import transaction
        from notebook.clients.models import Client
        with transaction.atomic():
            client = Client.objects.select_for_update().get(pk=self.client.pk)
            amount = self.amount
            if client.advance_balance >= amount:
                client.advance_balance -= amount
            else:
                remaining = amount - client.advance_balance
                client.advance_balance = Decimal('0')
                client.total_debt += remaining
            client.save(update_fields=['total_debt', 'advance_balance'])
            self.is_cancelled = True
            self.cancelled_at = timezone.now()
            self.cancelled_by = cancelled_by
            self.save(update_fields=['is_cancelled', 'cancelled_at', 'cancelled_by'])

    def __str__(self):
        return f"{self.client.name} — {self.amount} so'm"


class PaymentRefund(models.Model):
    payment    = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='refunds')
    amount     = models.DecimalField(max_digits=12, decimal_places=2)
    user       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    reason     = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "To'lov qaytarish"
        verbose_name_plural = "To'lov qaytarishlar"

    def __str__(self):
        return f"Refund {self.amount} — Payment #{self.payment.id}"
