# notebook/company/models.py
from django.db import models
from django.conf import settings
from notebook.core.managers import SoftDeleteManager


class Company(models.Model):
    business        = models.ForeignKey(
        'business.Business', on_delete=models.CASCADE,
        related_name='companies', verbose_name="Biznes",
        null=True, blank=True,  # eski yozuvlar uchun migratsiya vaqtida
    )
    name            = models.CharField(max_length=200, verbose_name="Nomi")
    phone           = models.CharField(max_length=20, blank=True)
    address         = models.TextField(blank=True)
    note            = models.TextField(blank=True)
    total_debt      = models.DecimalField(max_digits=14, decimal_places=2, default=0,
                                          verbose_name="Bizning qarzimiz")
    advance_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0,
                                          verbose_name="Avansimiz (ortiqcha to'lov)")
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='created_companies'
    )

    objects     = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ['name']
        verbose_name = "Kompaniya"
        verbose_name_plural = "Kompaniyalar"

    def __str__(self):
        return self.name


class Branch(models.Model):
    company         = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='branches')
    name            = models.CharField(max_length=200, verbose_name="Filial nomi")
    phone           = models.CharField(max_length=20, blank=True)
    address         = models.TextField(blank=True)
    note            = models.TextField(blank=True)
    total_debt      = models.DecimalField(max_digits=14, decimal_places=2, default=0,
                                          verbose_name="Bizning qarzimiz (filialga)")
    advance_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0,
                                          verbose_name="Avansimiz (ortiqcha to'lov)")
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='created_branches'
    )

    objects     = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ['company__name', 'name']
        verbose_name = "Filial"
        verbose_name_plural = "Filiallar"

    def __str__(self):
        return f"{self.company.name} — {self.name}"


class BranchPayment(models.Model):
    PAYMENT_TYPES = [
        ('cash',     'Naqd'),
        ('transfer', "O'tkazma"),
        ('discount', 'Chegirma'),
    ]

    branch           = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='payments')
    amount           = models.DecimalField(max_digits=14, decimal_places=2)
    payment_type     = models.CharField(max_length=20, choices=PAYMENT_TYPES, default='cash')
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    due_date         = models.DateField(null=True, blank=True)
    note             = models.CharField(max_length=255, blank=True)
    user             = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='branch_payments'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Filialga to'lov"
        verbose_name_plural = "Filialga to'lovlar"

    def __str__(self):
        return f"{self.branch} — {self.amount:,.0f} so'm"
