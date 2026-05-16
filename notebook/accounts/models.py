# apps/accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = (
        ("superadmin", "Super Admin"),
        ("admin",      "Admin"),
        ("staff",      "Xodim"),
    )
    role = models.CharField(max_length=12, choices=ROLE_CHOICES, default="staff")
    is_active = models.BooleanField(default=True)   # soft delete uchun
    fired_at = models.DateTimeField(null=True, blank=True)
    fired_by = models.ForeignKey(
        'self', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='fired_users'
    )
    phone = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_superadmin(self):
        return self.role == 'superadmin'

    @property
    def is_admin(self):
        return self.role in ('superadmin', 'admin')

    def fire(self, fired_by=None):
        from django.utils import timezone
        self.is_active = False
        self.fired_at  = timezone.now()
        self.fired_by  = fired_by
        self.save(update_fields=['is_active', 'fired_at', 'fired_by'])

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"