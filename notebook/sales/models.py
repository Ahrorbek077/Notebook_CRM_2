# notebook/sales/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone
from notebook.core.managers import NotCancelledManager


class Sale(models.Model):
    STATUS_ACTIVE    = 'active'
    STATUS_CANCELLED = 'cancelled'
    STATUS_CHOICES   = [
        (STATUS_ACTIVE,    'Faol'),
        (STATUS_CANCELLED, 'Bekor qilingan'),
    ]

    client       = models.ForeignKey('clients.Client', on_delete=models.PROTECT, related_name='sales')
    business     = models.ForeignKey(
        'business.Business', on_delete=models.CASCADE,
        related_name='sales', null=True, blank=True, verbose_name="Biznes"
    )
    user         = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    created_at   = models.DateTimeField(auto_now_add=True)

    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='cancelled_sales'
    )

    objects        = models.Manager()
    active_objects = NotCancelledManager()

    class Meta:
        verbose_name = "Sotuv"
        verbose_name_plural = "Sotuvlar"

    @property
    def item_count(self):
        from django.db.models import Sum
        return self.items.aggregate(t=Sum('quantity'))['t'] or 0

    def cancel(self, cancelled_by=None):
        if self.status == self.STATUS_CANCELLED:
            return
        self.status       = self.STATUS_CANCELLED
        self.cancelled_at = timezone.now()
        self.cancelled_by = cancelled_by
        self.save(update_fields=['status', 'cancelled_at', 'cancelled_by'])

    def full_cancel(self, cancelled_by=None, reason=""):
        if self.status == self.STATUS_CANCELLED:
            return
        from .services import SaleService
        return SaleService.full_cancel_sale(sale=self, cancelled_by=cancelled_by, reason=reason)

    def __str__(self):
        return f"Sale #{self.id} — {self.client.name}"


class SaleItem(models.Model):
    sale               = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    product            = models.ForeignKey('catalog.Product', on_delete=models.PROTECT)
    batch              = models.ForeignKey(
        'inventory.StockBatch', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='sale_items'
    )
    quantity           = models.DecimalField(max_digits=10, decimal_places=3)
    price_at_sale      = models.DecimalField(max_digits=10, decimal_places=2)
    cost_price_at_sale = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    returned_quantity  = models.DecimalField(max_digits=10, decimal_places=3, default=0)

    class Meta:
        indexes = [models.Index(fields=['sale'])]

    def subtotal(self):
        return self.quantity * self.price_at_sale

    def profit(self):
        return (self.quantity - self.returned_quantity) * (self.price_at_sale - self.cost_price_at_sale)

    def get_remaining_quantity(self):
        return self.quantity - self.returned_quantity


class SaleReturn(models.Model):
    sale       = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='returns')
    user       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    reason     = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Qaytarish"
        verbose_name_plural = "Qaytarishlar"

    def __str__(self):
        return f"Qaytarish #{self.id} — Sale #{self.sale.id}"


class SaleReturnItem(models.Model):
    sale_return       = models.ForeignKey(SaleReturn, on_delete=models.CASCADE, related_name='items')
    sale_item         = models.ForeignKey(SaleItem, on_delete=models.CASCADE)
    returned_quantity = models.DecimalField(max_digits=10, decimal_places=3)
    returned_to_batch = models.ForeignKey(
        'inventory.StockBatch', on_delete=models.SET_NULL, null=True
    )

    def __str__(self):
        return f"{self.returned_quantity} ta {self.sale_item.product.name}"