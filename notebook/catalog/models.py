# notebook/catalog/models.py
"""
Category, Region, Product — faqat katalog modellari.
"""
from django.db import models
from django.conf import settings
from django_resized import ResizedImageField
from notebook.core.managers import SoftDeleteManager
from notebook.core.utils import smart_slug


class Category(models.Model):
    name      = models.CharField(max_length=100, verbose_name="Nomi")
    is_active = models.BooleanField(default=True)

    objects     = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name        = "Kategoriya"
        verbose_name_plural = "Kategoriyalar"

    def __str__(self):
        return self.name

    @property
    def latest_cost_price(self):
        """Eng oxirgi StockBatch tan narxini qaytaradi.
        Batch yo'q bo'lsa default_cost_price ni qaytaradi."""
        batch = self.stock_batches.filter(is_active=True).order_by('-created_at').first()
        return batch.cost_price if batch else self.default_cost_price


class Product(models.Model):
    name     = models.CharField(max_length=200, verbose_name="Nomi")
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT,
        related_name='products', verbose_name="Kategoriya"
    )
    branch   = models.ForeignKey(
        'company.Branch', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='products', verbose_name="Filial"
    )
    slug  = models.SlugField(max_length=256, unique=True, blank=True, allow_unicode=True)
    image = ResizedImageField(
        size=[756, 741], crop=['middle', 'center'],
        upload_to='products/%Y/%m',
        null=True, blank=True,
    )
    price = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name="Sotuv narxi"
    )
    default_cost_price = models.DecimalField(
        max_digits=10, decimal_places=2,
        default=0,
        verbose_name="Standart tan narxi",
        help_text="Yaratishda kiritilgan tan narxi — Sotib olish modalida default sifatida ko'rsatiladi"
    )
    stock = models.PositiveIntegerField(default=0, editable=False)

    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='created_products'
    )

    objects     = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name        = "Mahsulot"
        verbose_name_plural = "Mahsulotlar"

    def save(self, *args, **kwargs):
        # Slug faqat yaratishda yoki bo'sh bo'lsa generatsiya qilinadi
        if not self.slug or not self.pk:
            base = smart_slug(self.name)   # ← Kirill, Lotin, unicode — barchasi ishlaydi
            slug = base
            n    = 1
            while Product.all_objects.filter(slug=slug).exists():
                slug = f"{base}-{n}"
                n   += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    @property
    def latest_cost_price(self):
        """Eng oxirgi StockBatch tan narxini qaytaradi.
        Batch yo'q bo'lsa default_cost_price ni qaytaradi."""
        batch = self.stock_batches.filter(is_active=True).order_by('-created_at').first()
        return batch.cost_price if batch else self.default_cost_price