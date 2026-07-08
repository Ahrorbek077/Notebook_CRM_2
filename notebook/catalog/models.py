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
    business  = models.ForeignKey(
        'business.Business', on_delete=models.CASCADE,
        related_name='categories', verbose_name="Biznes",
        null=True, blank=True,  # eski yozuvlar uchun migratsiya vaqtida
    )
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
    UNIT_DONA = 'dona'
    UNIT_KG   = 'kg'
    UNIT_CHOICES = [
        (UNIT_DONA, 'Dona'),
        (UNIT_KG,   'Kilogram'),
    ]

    name     = models.CharField(max_length=200, verbose_name="Nomi")
    business = models.ForeignKey(
        'business.Business', on_delete=models.CASCADE,
        related_name='products', verbose_name="Biznes",
        null=True, blank=True,  # eski yozuvlar uchun migratsiya vaqtida
    )
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT,
        related_name='products', verbose_name="Kategoriya"
    )
    branch   = models.ForeignKey(
        'company.Branch', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='products', verbose_name="Filial"
    )
    unit_type = models.CharField(
        max_length=10, choices=UNIT_CHOICES, default=UNIT_DONA,
        verbose_name="O'lchov birligi",
        help_text="Mahsulot dona yoki kilogramda sotiladimi"
    )
    is_box_enabled = models.BooleanField(
        default=False,
        verbose_name="Karobkalab sotiladi/olinadi",
        help_text="Yoqilsa, xarid va sotuvda 'Karobkalab' rejimi ham ko'rinadi"
    )
    units_per_box = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True,
        verbose_name="1 karobkadagi miqdor",
        help_text="1 karobkada nechta dona/kg bo'ladi (doimiy, mahsulot uchun bir marta belgilanadi)"
    )
    slug  = models.SlugField(max_length=256, blank=True, allow_unicode=True)
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
    stock = models.DecimalField(
        max_digits=10, decimal_places=3, default=0, editable=False,
        verbose_name="Qoldiq", help_text="Dona yoki kg (unit_type ga qarab)"
    )

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
        unique_together     = [('business', 'slug')]

    def save(self, *args, **kwargs):
        # Slug faqat yaratishda yoki bo'sh bo'lsa generatsiya qilinadi
        if not self.slug or not self.pk:
            base = smart_slug(self.name)   # ← Kirill, Lotin, unicode — barchasi ishlaydi
            slug = base
            n    = 1
            while Product.all_objects.filter(business=self.business, slug=slug).exclude(pk=self.pk).exists():
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

    @property
    def stock_boxes(self):
        """Stokdagi TO'LIQ karobkalar soni. Karobka o'chiq bo'lsa None."""
        if self.is_box_enabled and self.units_per_box:
            return int(self.stock // self.units_per_box)
        return None

    @property
    def stock_box_remainder(self):
        """Karobkalarga sig'may qolgan qoldiq (dona/kg)."""
        if self.is_box_enabled and self.units_per_box:
            return self.stock - (self.stock // self.units_per_box) * self.units_per_box
        return None