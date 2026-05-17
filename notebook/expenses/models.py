# notebook/expenses/models.py
from django.db import models
from django.conf import settings


class PersonalExpense(models.Model):
    """
    Foydalanuvchining shaxsiy chiqimlari.
    Biznes hisobiga (sales, payments, inventory) HECH QANDAY aloqasi yo'q.

    category — ixtiyoriy matn izohi, filterlash uchun.
    Misol: "Transport", "Ovqat", "Ko'ngil ochar" — foydalanuvchi xohlaganicha yozadi.
    """
    user        = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='personal_expenses', verbose_name="Foydalanuvchi"
    )
    category    = models.CharField(
        max_length=100, blank=True, default='',
        verbose_name="Kategoriya (izoh)",
        help_text="Ixtiyoriy. Masalan: Transport, Ovqat, Ko'ngil ochar"
    )
    amount      = models.DecimalField(
        max_digits=14, decimal_places=2, verbose_name="Miqdor (so'm)"
    )
    description = models.CharField(max_length=255, verbose_name="Tavsif")
    date        = models.DateField(verbose_name="Sana")
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name = "Shaxsiy chiqim"
        verbose_name_plural = "Shaxsiy chiqimlar"

    def __str__(self):
        return f"{self.user.username} — {self.description}: {self.amount:,.0f} so'm"
