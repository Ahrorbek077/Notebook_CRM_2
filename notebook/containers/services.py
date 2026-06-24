# notebook/containers/services.py
"""
ContainerService — idish berish/qaytarish biznes logikasi.

Barcha amallar atomik (transaction.atomic) va select_for_update bilan —
bir vaqtda ikki operator ishlasa ham raqamlar to'g'ri qoladi (race condition yo'q).
"""
from django.db import transaction
from notebook.activity.models import ActivityLog
from .models import BranchContainerStock, ClientContainer, ContainerTransaction


class ContainerService:

    @staticmethod
    def give(client, branch, container_type, quantity: int, user=None, note=""):
        """Mijozga idish berish.

        Filial omboridan kamayadi, mijozda ko'payadi.
        Agar filial omborida yetarli bo'lmasa — ValueError.
        """
        if quantity <= 0:
            raise ValueError("Miqdor 0 dan katta bo'lishi kerak")

        with transaction.atomic():
            # ── Filial ombori — lock bilan o'qiymiz (race condition oldini olish) ──
            branch_stock, _ = BranchContainerStock.objects.select_for_update().get_or_create(
                branch=branch, container_type=container_type,
                defaults={'quantity': 0}
            )
            if branch_stock.quantity < quantity:
                raise ValueError(
                    f"Omborda yetarli {container_type.name} yo'q "
                    f"(bor: {branch_stock.quantity}, kerak: {quantity})"
                )

            branch_stock.quantity -= quantity
            branch_stock.save(update_fields=['quantity'])

            # ── Mijozdagi idish — lock bilan ────────────────────────────────────
            client_container, _ = ClientContainer.objects.select_for_update().get_or_create(
                client=client, container_type=container_type,
                defaults={'quantity': 0}
            )
            client_container.quantity += quantity
            client_container.save(update_fields=['quantity'])

            # ── Tarix yozuvi ─────────────────────────────────────────────────────
            tx = ContainerTransaction.objects.create(
                client=client, branch=branch, container_type=container_type,
                action=ContainerTransaction.ACTION_GIVEN,
                quantity=quantity, note=note, user=user,
            )
            ActivityLog.objects.create(
                user=user, business=client.business, action_type='container_given',
                description=f"{client.name} ga {quantity} ta {container_type.name} berildi",
                extra_data={
                    'client_id': client.id, 'client_name': client.name,
                    'branch_id': branch.id, 'branch_name': str(branch),
                    'container_type': container_type.name, 'quantity': str(quantity),
                    'note': note,
                }
            )
            return tx

    @staticmethod
    def return_containers(client, branch, container_type, quantity: int, user=None, note=""):
        """Mijozdan idish qaytarib olish.

        Mijozda kamayadi, filial omboriga qaytadi.
        Agar mijozda yetarli bo'lmasa (masalan ko'p qaytarmoqchi) — ValueError.
        """
        if quantity <= 0:
            raise ValueError("Miqdor 0 dan katta bo'lishi kerak")

        with transaction.atomic():
            client_container, _ = ClientContainer.objects.select_for_update().get_or_create(
                client=client, container_type=container_type,
                defaults={'quantity': 0}
            )
            if client_container.quantity < quantity:
                raise ValueError(
                    f"Mijozda yetarli {container_type.name} yo'q "
                    f"(bor: {client_container.quantity}, qaytarilmoqchi: {quantity})"
                )

            client_container.quantity -= quantity
            client_container.save(update_fields=['quantity'])

            branch_stock, _ = BranchContainerStock.objects.select_for_update().get_or_create(
                branch=branch, container_type=container_type,
                defaults={'quantity': 0}
            )
            branch_stock.quantity += quantity
            branch_stock.save(update_fields=['quantity'])

            tx = ContainerTransaction.objects.create(
                client=client, branch=branch, container_type=container_type,
                action=ContainerTransaction.ACTION_RETURNED,
                quantity=quantity, note=note, user=user,
            )
            ActivityLog.objects.create(
                user=user, business=client.business, action_type='container_returned',
                description=f"{client.name} dan {quantity} ta {container_type.name} qaytarib olindi",
                extra_data={
                    'client_id': client.id, 'client_name': client.name,
                    'branch_id': branch.id, 'branch_name': str(branch),
                    'container_type': container_type.name, 'quantity': str(quantity),
                    'note': note,
                }
            )
            return tx

    @staticmethod
    def add_to_branch_stock(branch, container_type, quantity: int, user=None):
        """Filial omboriga yangi idish qo'shish (masalan ishlab chiqarishdan keldi).

        Bu — boshlang'ich/qo'shimcha to'ldirish, mijoz bilan bog'liq emas.
        """
        if quantity <= 0:
            raise ValueError("Miqdor 0 dan katta bo'lishi kerak")

        with transaction.atomic():
            branch_stock, _ = BranchContainerStock.objects.select_for_update().get_or_create(
                branch=branch, container_type=container_type,
                defaults={'quantity': 0}
            )
            branch_stock.quantity += quantity
            branch_stock.save(update_fields=['quantity'])

            ActivityLog.objects.create(
                user=user, business=branch.company.business, action_type='container_stock_add',
                description=f"{branch} omboriga {quantity} ta {container_type.name} qo'shildi",
                extra_data={
                    'branch_id': branch.id, 'branch_name': str(branch),
                    'container_type': container_type.name, 'quantity': str(quantity),
                    'new_stock': str(branch_stock.quantity),
                }
            )
            return branch_stock

    @staticmethod
    def get_client_summary(client):
        """Mijozdagi barcha idish turlarini qaytaradi: [{'type': ..., 'quantity': ...}]"""
        return list(
            client.containers.select_related('container_type')
                  .filter(quantity__gt=0)
                  .values('container_type__id', 'container_type__name', 'quantity')
        )

    @staticmethod
    def get_branch_summary(branch):
        """Filial omboridagi barcha idish turlarini qaytaradi."""
        return list(
            branch.container_stocks.select_related('container_type')
                  .values('container_type__id', 'container_type__name', 'quantity')
        )