# notebook/activity/models.py
from django.db import models
from django.conf import settings


class ActivityLog(models.Model):
    ACTION_CHOICES = [
        # Company / Branch
        ('company_create', "Kompaniya qo'shildi"),
        ('company_update', "Kompaniya yangilandi"),
        ('company_delete', "Kompaniya o'chirildi"),
        ('branch_create',  "Filial qo'shildi"),
        ('branch_update',  "Filial yangilandi"),
        ('branch_delete',  "Filial o'chirildi"),
        ('branch_payment', "Filialga to'lov qilindi"),
        # Product
        ('product_create', "Mahsulot qo'shildi"),
        ('product_update', "Mahsulot yangilandi"),
        ('product_delete', "Mahsulot o'chirildi"),
        # Stock
        ('stock_add',    'Stock kirim qilindi'),
        ('stock_adjust', 'Stock tuzatildi'),
        ('stock_delete', "Batch o'chirildi"),
        ('stock_return', 'Omborga qaytarish (batch)'),
        # Sale
        ('sale',         'Sotuv amalga oshirildi'),
        ('sale_return',  'Sotuv qaytarildi'),
        # Payment
        ('payment',        "To'lov qabul qilindi"),
        ('payment_refund', "To'lov qaytarildi"),
        # Client
        ('client_create', "Mijoz qo'shildi"),
        ('client_update', "Mijoz yangilandi"),
        ('client_delete', "Mijoz o'chirildi"),
    ]

    user        = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    action_type = models.CharField(max_length=30, choices=ACTION_CHOICES)
    description = models.CharField(max_length=255)
    extra_data  = models.JSONField(null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering     = ['-created_at']
        indexes      = [models.Index(fields=['-created_at'])]
        verbose_name = "Faoliyat"
        verbose_name_plural = "Faoliyat tarixi"

    def __str__(self):
        return f"{self.created_at:%d.%m.%Y %H:%M} — {self.get_action_type_display()}"
