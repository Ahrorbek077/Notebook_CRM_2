# notebook/payments/services.py
from decimal import Decimal
from django.db import transaction
from django.core.cache import cache
from django.db.transaction import on_commit
from .models import Payment, PaymentRefund


class PaymentService:

    @staticmethod
    def create_payment(client, amount: Decimal, user=None, note="") -> Payment:
        from notebook.clients.models import Client
        from notebook.activity.models import ActivityLog
        if amount <= 0:
            raise ValueError("To'lov summasi musbat bo'lishi kerak")

        with transaction.atomic():
            client = Client.objects.select_for_update().get(pk=client.pk)
            payment = Payment.objects.create(client=client, amount=amount, user=user, note=note)

            if client.total_debt >= amount:
                client.total_debt -= amount
            else:
                remaining = amount - client.total_debt
                client.total_debt = Decimal('0')
                client.advance_balance += remaining
            client.save(update_fields=['total_debt', 'advance_balance'])

            ActivityLog.objects.create(
                user=user, action_type='payment',
                description=f"{client.name} — {amount:,.0f} so'm to'lov",
                extra_data={'payment_id': payment.id, 'client_id': client.id,
                            'client_name': client.name, 'amount': str(amount), 'note': note}
            )
            cache.delete('dashboard_full_data')
            on_commit(lambda: _refresh_mv())
            return payment

    @staticmethod
    def refund_payment(payment: Payment, amount: Decimal, user=None, reason="") -> Payment:
        from notebook.clients.models import Client
        from notebook.activity.models import ActivityLog
        if amount <= 0:
            raise ValueError("Qaytarish summasi musbat bo'lishi kerak")
        if amount > payment.get_remaining_amount():
            raise ValueError(f"Maksimal qaytarish: {payment.get_remaining_amount()} so'm")

        with transaction.atomic():
            payment = Payment.objects.select_for_update().get(pk=payment.pk)
            client  = Client.objects.select_for_update().get(pk=payment.client.pk)

            PaymentRefund.objects.create(payment=payment, amount=amount, user=user, reason=reason)
            payment.refunded_amount += amount
            payment.save(update_fields=['refunded_amount'])

            if client.advance_balance >= amount:
                client.advance_balance -= amount
            else:
                remaining = amount - client.advance_balance
                client.advance_balance = Decimal('0')
                client.total_debt += remaining
            client.save(update_fields=['total_debt', 'advance_balance'])

            ActivityLog.objects.create(
                user=user, action_type='payment_refund',
                description=f"{client.name} — {amount:,.0f} so'm to'lov qaytarildi",
                extra_data={'refund_id': None, 'payment_id': payment.id,
                            'client_name': client.name, 'amount': str(amount), 'reason': reason}
            )
            cache.delete('dashboard_full_data')
            on_commit(lambda: _refresh_mv())
            return payment


def _refresh_mv():
    try:
        from notebook.dashboard.tasks import refresh_materialized_views
        refresh_materialized_views.delay()
    except Exception:
        pass
