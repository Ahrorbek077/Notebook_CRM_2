# notebook/clients/models.py
# O'zgarish: latitude va longitude maydonlari qo'shildi
from django.db import models
from django.conf import settings
from django.db.models import Sum
from decimal import Decimal
from notebook.core.managers import SoftDeleteManager


class Region(models.Model):
    name      = models.CharField(max_length=100, unique=True, verbose_name="Nomi")
    is_active = models.BooleanField(default=True)
    order     = models.PositiveSmallIntegerField(default=0)

    objects     = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ['order', 'name']
        verbose_name = "Viloyat"
        verbose_name_plural = "Viloyatlar"

    def __str__(self):
        return self.name


class Client(models.Model):
    name            = models.CharField(max_length=200, verbose_name="Ismi")
    phone           = models.CharField(max_length=20, verbose_name="Telefon")
    address         = models.TextField(blank=True, verbose_name="Manzil")

    # ── Google Maps koordinatalari (ixtiyoriy) ─────────────────────────────
    latitude        = models.DecimalField(
        max_digits=9, decimal_places=6,
        null=True, blank=True, verbose_name="Kenglik (lat)"
    )
    longitude       = models.DecimalField(
        max_digits=9, decimal_places=6,
        null=True, blank=True, verbose_name="Uzunlik (lng)"
    )

    region          = models.ForeignKey(
        Region, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='clients', verbose_name="Viloyat"
    )
    total_debt      = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Qarzi")
    advance_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Avans")

    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='created_clients'
    )

    objects     = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = "Mijoz"
        verbose_name_plural = "Mijozlar"

    def __str__(self):
        return self.name

    @property
    def has_location(self):
        """Koordinata mavjudligini tekshiradi."""
        return self.latitude is not None and self.longitude is not None

    @property
    def google_maps_url(self):
        """Google Maps ga to'g'ridan link."""
        if self.has_location:
            return f"https://www.google.com/maps?q={self.latitude},{self.longitude}"
        return None

    def recalculate_balances(self):
        total_sales    = self.sales.aggregate(t=Sum('total_amount'))['t'] or Decimal('0')
        total_payments = self.payments.aggregate(t=Sum('amount'))['t']    or Decimal('0')
        debt = total_sales - total_payments
        self.total_debt      = max(debt,  Decimal('0'))
        self.advance_balance = max(-debt, Decimal('0'))
        self.save(update_fields=['total_debt', 'advance_balance'])
