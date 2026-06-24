# notebook/inventory/models.py
from django.db import models
from django.conf import settings


class StockBatch(models.Model):
    """FIFO qatlami. Har bir xaridda yangi batch yaratiladi.

    MUHIM: quantity_received / remaining_quantity har doim mahsulotning
    ENG KICHIK birligida saqlanadi (dona yoki kg) — FIFO, sotuv, return,
    dashboard hisoblari shu asosda ishlaydi va o'zgarishsiz qoladi.

    box_quantity / units_per_box — faqat TARIXIY ma'lumot:
    "necha karobka kelgan, har karobkada nechta birlik bo'lgan".
    Hisob-kitobga ta'sir qilmaydi, faqat ko'rsatish uchun.
    """
    product           = models.ForeignKey(
        'catalog.Product', on_delete=models.PROTECT,
        related_name='stock_batches', verbose_name="Mahsulot"
    )
    business          = models.ForeignKey(
        'business.Business', on_delete=models.CASCADE,
        related_name='stock_batches', null=True, blank=True, verbose_name="Biznes"
    )
    branch            = models.ForeignKey(
        'company.Branch', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='stock_batches', verbose_name="Filial"
    )
    quantity_received  = models.DecimalField(
        max_digits=10, decimal_places=3, verbose_name="Qabul qilingan"
    )
    remaining_quantity = models.DecimalField(
        max_digits=10, decimal_places=3, verbose_name="Qoldiq"
    )
    cost_price         = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Tan narxi",
        help_text="1 birlik (dona/kg) tan narxi"
    )
    selling_price      = models.DecimalField(
        max_digits=10, decimal_places=2,
        help_text="Sotib olingan paytdagi sotuv narxi (snapshot)",
        verbose_name="Sotuv narxi (snapshot)"
    )
    # ── Karobka tarixi (faqat ko'rsatish uchun, hisobga ta'sir qilmaydi) ────
    box_quantity  = models.PositiveIntegerField(
        null=True, blank=True,
        verbose_name="Karobka soni",
        help_text="Necha karobka sotib olingan (agar karobkalab olingan bo'lsa)"
    )
    units_per_box = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True,
        verbose_name="1 karobkadagi miqdor",
        help_text="1 karobkada nechta dona/kg bo'lgan"
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
    quantity_change = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    new_cost_price  = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    reason          = models.TextField(blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Stock tuzatish"
        verbose_name_plural = "Stock tuzatishlar"

    def __str__(self):
        return f"Adjustment #{self.id} — Batch #{self.batch.id}"