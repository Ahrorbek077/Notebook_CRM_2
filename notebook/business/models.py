# notebook/business/models.py
"""
Business — "Aka" va "Ukalar" kabi har bir alohida biznesni ifodalaydi.

Mantiq:
  - Har bir Business — to'liq mustaqil hisob-kitob doirasi: o'z mijozlari,
    mahsulotlari, sotuvlari, ombori, xarajatlari, to'lovlari bo'ladi.
  - Har bir User (admin/staff) FAQAT BITTA Business'ga tegishli bo'ladi
    (accounts.User.business). Shu Business doirasidan tashqarini ko'rmaydi.
  - Superadmin (aka) ham o'z Business'iga tegishli, LEKIN session orqali
    boshqa Business'larga "almashish" (switch) imkoniga ega — request.business
    shu tanlovga qarab o'rnatiladi (notebook.business.middleware).
  - Boshqa app'lar (clients, catalog, inventory, sales, payments, expenses,
    company, containers, activity) o'z modellariga `business` FK qo'shib,
    shu Business orqali bir-biridan TO'LIQ ajratiladi.
"""
from django.conf import settings
from django.db import models
from django.utils.text import slugify


class Business(models.Model):
    name       = models.CharField(max_length=200, verbose_name="Nomi")
    slug       = models.SlugField(max_length=220, unique=True, blank=True, allow_unicode=True)
    owner      = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='owned_businesses',
        verbose_name="Egasi",
        help_text="Shu biznesning asosiy egasi (masalan, uka)"
    )
    phone      = models.CharField(max_length=20, blank=True)
    note       = models.TextField(blank=True)
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    webhook_token = models.CharField(
        max_length=40, unique=True, blank=True,
        verbose_name="Webhook token",
        help_text="Bank SMS/bildirishnoma avtomatlashtirish (MacroDroid) uchun maxfiy kalit"
    )

    class Meta:
        ordering = ['name']
        verbose_name = "Biznes"
        verbose_name_plural = "Bizneslar"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name, allow_unicode=True) or "biznes"
            slug = base
            n = 1
            while Business.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{n}"
                n += 1
            self.slug = slug
        if not self.webhook_token:
            import secrets
            self.webhook_token = secrets.token_urlsafe(24)
        super().save(*args, **kwargs)
