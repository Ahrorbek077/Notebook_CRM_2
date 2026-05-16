# notebook/inventory/models.py
from django.db import models
from django.conf import settings


class StockBatch(models.Model):
    """FIFO qatlami. Har bir xaridda yangi batch yaratiladi."""
    product           = models.ForeignKey(
        'catalog.Product', on_delete=models.PROTECT,
        related_name='stock_batches', verbose_name="Mahsulot"
    )
    branch            = models.ForeignKey(
        'company.Branch', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='stock_batches', verbose_name="Filial"
    )
    quantity_received  = models.PositiveIntegerField(verbose_name="Qabul qilingan")
    remaining_quantity = models.PositiveIntegerField(verbose_name="Qoldiq")
    cost_price         = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Tan narxi")
    selling_price      = models.DecimalField(
        max_digits=10, decimal_places=2,
        help_text="Sotib olingan paytdagi sotuv narxi (snapshot)",
        verbose_name="Sotuv narxi (snapshot)"
    )
    is_active          = models.BooleanField(default=True)
    created_at         = models.DateTimeField(auto_now_add=True)
    created_by         = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='created_batches'
    )

    class Meta:
        ordering = ['created_at']
        indexes  = [models.Index(fields=['product', 'created_at'])]
        verbose_name = "Stock Batch"
        verbose_name_plural = "Stock Batch'lar"

    def __str__(self):
        return f"{self.product.name} — {self.remaining_quantity}/{self.quantity_received} @ {self.cost_price}"

    def soft_delete(self):
        if self.remaining_quantity > 0:
            raise ValueError(f"Batchda {self.remaining_quantity} ta qoldiq bor — o'chirib bo'lmaydi")
        self.is_active = False
        self.save(update_fields=['is_active'])


class StockAdjustment(models.Model):
    ADJUSTMENT_TYPES = [
        ('increase',     'Miqdorni oshirish'),
        ('decrease',     'Miqdorni kamaytirish'),
        ('price_change', "Narxni o'zgartirish"),
        ('correction',   "To'liq tuzatish"),
        ('return',       'Sotuv qaytarish'),
    ]

    batch           = models.ForeignKey(StockBatch, on_delete=models.CASCADE, related_name='adjustments')
    user            = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    adjustment_type = models.CharField(max_length=20, choices=ADJUSTMENT_TYPES)
    quantity_change = models.IntegerField(null=True, blank=True)
    new_cost_price  = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    reason          = models.TextField(blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Stock tuzatish"
        verbose_name_plural = "Stock tuzatishlar"

    def __str__(self):
        return f"Adjustment #{self.id} — Batch #{self.batch.id}"
