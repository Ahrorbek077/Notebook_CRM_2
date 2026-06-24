# notebook/containers/models.py
"""
Idish (qayta foydalaniladigan idish-tara) ijara tizimi.

Mantiq:
  ContainerType        — idish turi (Katta plastik, Kichik plastik, Temir...)
  BranchContainerStock — har filialning OMBORIDA qancha idish bor
  ClientContainer      — har MIJOZDA hozir qancha idish bor (qaytarilmagan)
  ContainerTransaction — har bir berish/qaytarish amalining TARIXI

Oqim:
  Filial omborida 1000 ta bor → mijozga 20 ta BERILDI:
      BranchContainerStock.quantity  -= 20   (980 qoldi)
      ClientContainer.quantity       += 20   (mijozda 20 bor)
      ContainerTransaction yaratiladi (action='given', quantity=20)

  Mijoz 6 tasini QAYTARDI:
      BranchContainerStock.quantity  += 6    (986 bo'ldi)
      ClientContainer.quantity       -= 6    (mijozda 14 qoldi)
      ContainerTransaction yaratiladi (action='returned', quantity=6)
"""
from django.db import models
from django.conf import settings


class ContainerType(models.Model):
    """Idish turi — masalan 'Katta plastik', 'Kichik plastik', 'Temir'."""
    business   = models.ForeignKey(
        'business.Business', on_delete=models.CASCADE,
        related_name='container_types', verbose_name="Biznes",
        null=True, blank=True,  # eski yozuvlar uchun migratsiya vaqtida
    )
    name       = models.CharField(max_length=100, verbose_name="Nomi")
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        unique_together = [('business', 'name')]
        verbose_name = "Idish turi"
        verbose_name_plural = "Idish turlari"

    def __str__(self):
        return self.name


class BranchContainerStock(models.Model):
    """Filial omboridagi idish miqdori — har (filial, idish turi) uchun bitta yozuv."""
    branch         = models.ForeignKey(
        'company.Branch', on_delete=models.CASCADE,
        related_name='container_stocks', verbose_name="Filial"
    )
    container_type = models.ForeignKey(
        ContainerType, on_delete=models.PROTECT,
        related_name='branch_stocks', verbose_name="Idish turi"
    )
    quantity       = models.PositiveIntegerField(default=0, verbose_name="Omborda qoldi")
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('branch', 'container_type')]
        verbose_name = "Filial idish ombori"
        verbose_name_plural = "Filial idish omborlari"

    def __str__(self):
        return f"{self.branch.name} — {self.container_type.name}: {self.quantity}"


class ClientContainer(models.Model):
    """Mijozda hozir qancha idish bor (qaytarilmagan) — har (mijoz, idish turi) uchun bitta yozuv."""
    client         = models.ForeignKey(
        'clients.Client', on_delete=models.CASCADE,
        related_name='containers', verbose_name="Mijoz"
    )
    container_type = models.ForeignKey(
        ContainerType, on_delete=models.PROTECT,
        related_name='client_holdings', verbose_name="Idish turi"
    )
    quantity       = models.PositiveIntegerField(default=0, verbose_name="Mijozda bor")
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('client', 'container_type')]
        verbose_name = "Mijozdagi idish"
        verbose_name_plural = "Mijozlardagi idishlar"

    def __str__(self):
        return f"{self.client.name} — {self.container_type.name}: {self.quantity}"


class ContainerTransaction(models.Model):
    """Har bir berish/qaytarish amalining tarixi — audit uchun o'chmaydi."""
    ACTION_GIVEN    = 'given'
    ACTION_RETURNED = 'returned'
    ACTION_CHOICES  = [
        (ACTION_GIVEN,    'Berildi'),
        (ACTION_RETURNED, 'Qaytarildi'),
    ]

    client         = models.ForeignKey(
        'clients.Client', on_delete=models.CASCADE,
        related_name='container_transactions', verbose_name="Mijoz"
    )
    branch         = models.ForeignKey(
        'company.Branch', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='container_transactions', verbose_name="Filial"
    )
    container_type = models.ForeignKey(
        ContainerType, on_delete=models.PROTECT,
        related_name='transactions', verbose_name="Idish turi"
    )
    action         = models.CharField(max_length=10, choices=ACTION_CHOICES, verbose_name="Amal")
    quantity       = models.PositiveIntegerField(verbose_name="Miqdor")
    note           = models.CharField(max_length=255, blank=True, verbose_name="Izoh")
    user           = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='container_transactions'
    )
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes  = [
            models.Index(fields=['client', 'created_at']),
            models.Index(fields=['branch', 'created_at']),
        ]
        verbose_name = "Idish tranzaksiyasi"
        verbose_name_plural = "Idish tranzaksiyalari"

    def __str__(self):
        sign = '+' if self.action == self.ACTION_GIVEN else '-'
        return f"{self.client.name} {sign}{self.quantity} {self.container_type.name}"
