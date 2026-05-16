# notebook/core/managers.py
"""
Barcha app'lar foydalanadigan umumiy Manager'lar.
"""
from django.db import models


class SoftDeleteManager(models.Manager):
    """Faqat is_active=True bo'lganlarni qaytaradi."""
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)

    def all_with_deleted(self):
        return super().get_queryset()


class NotCancelledManager(models.Manager):
    """Faqat is_cancelled=False bo'lganlarni qaytaradi."""
    def get_queryset(self):
        return super().get_queryset().filter(is_cancelled=False)
