# notebook/inventory/services.py
"""
StockService — FIFO ombor boshqaruvi.
"""
from decimal import Decimal
from django.db import transaction
from django.db.models import F
from .models import StockBatch, StockAdjustment


class StockService:

    @staticmethod
    def add_stock(product, quantity: int, cost_price: Decimal,
                  branch=None, user=None) -> StockBatch:
        """Yangi batch yaratish — omborga kirim."""
        if quantity <= 0 or cost_price <= 0:
            raise ValueError("Miqdor va narx musbat bo'lishi kerak")
        if not product.is_active:
            raise ValueError(f"{product.name} mahsuloti faol emas!")

        with transaction.atomic():
            batch = StockBatch.objects.create(
                product=product,
                branch=branch,
                quantity_received=quantity,
                remaining_quantity=quantity,
                cost_price=cost_price,
                selling_price=product.price,   # snapshot
                created_by=user,
            )
            product.stock = F('stock') + quantity
            product.save(update_fields=['stock'])
            return batch

    @staticmethod
    def adjust_stock(batch: StockBatch, quantity_change: int = 0,
                     new_cost_price: Decimal = None, user=None, reason="") -> StockAdjustment:
        """Batch tuzatish — faqat to'liq yangi (sarflanmagan) batch."""
        if batch.remaining_quantity != batch.quantity_received:
            raise ValueError("Sarflangan batchni o'zgartirib bo'lmaydi")

        with transaction.atomic():
            adj_type = (
                'price_change' if new_cost_price and quantity_change == 0 else
                'increase'     if quantity_change > 0 else
                'decrease'     if quantity_change < 0 else
                'correction'
            )
            adjustment = StockAdjustment.objects.create(
                batch=batch, user=user,
                adjustment_type=adj_type,
                quantity_change=quantity_change,
                new_cost_price=new_cost_price,
                reason=reason,
            )
            if quantity_change != 0:
                if batch.remaining_quantity + quantity_change < 0:
                    raise ValueError("Manfiy stock bo'lib qolyapti")
                batch.remaining_quantity += quantity_change
                batch.quantity_received  += quantity_change
                batch.save(update_fields=['remaining_quantity', 'quantity_received'])
                product = batch.product
                product.stock = F('stock') + quantity_change
                product.save(update_fields=['stock'])
            if new_cost_price and new_cost_price > 0:
                batch.cost_price = new_cost_price
                batch.save(update_fields=['cost_price'])
            return adjustment

    @staticmethod
    def consume_fifo(product, quantity: int) -> list:
        """FIFO chiqim — sotuv uchun. [{'batch', 'quantity', 'cost_price'}, ...]"""
        if quantity <= 0:
            return []
        if not product.is_active:
            raise ValueError(f"{product.name} mahsuloti faol emas!")

        with transaction.atomic():
            remaining = quantity
            result    = []
            batches   = StockBatch.objects.select_for_update().filter(
                product=product, remaining_quantity__gt=0, is_active=True,
            ).order_by('created_at')

            for batch in batches:
                if remaining <= 0:
                    break
                consume = min(remaining, batch.remaining_quantity)
                result.append({'batch': batch, 'quantity': consume, 'cost_price': batch.cost_price})
                batch.remaining_quantity -= consume
                batch.save(update_fields=['remaining_quantity'])
                remaining -= consume

            if remaining > 0:
                raise ValueError(f"{product.name} omborda yetarli emas!")

            product.stock = F('stock') - quantity
            product.save(update_fields=['stock'])
            return result

    @staticmethod
    def return_to_batch(batch: StockBatch, quantity: int, user=None, reason=""):
        """Sotuv qaytarilganda batchga qaytarish."""
        if quantity <= 0:
            return
        with transaction.atomic():
            if batch.remaining_quantity + quantity > batch.quantity_received:
                raise ValueError("Ortiqcha return bo'lyapti")
            batch.remaining_quantity += quantity
            batch.save(update_fields=['remaining_quantity'])
            batch.product.stock = F('stock') + quantity
            batch.product.save(update_fields=['stock'])
            StockAdjustment.objects.create(
                batch=batch, user=user,
                adjustment_type='return',
                quantity_change=quantity,
                reason=reason or "Return orqali qo'shildi",
            )

    @staticmethod
    def return_purchase(batch: StockBatch, quantity: int, user=None, reason=""):
        """
        Xarid qaytarish — sotib olingan mahsulotni kompaniyaga qaytarish.

        Nima bo'ladi:
          - batch.remaining_quantity    ↓  (omborda kamayadi)
          - batch.quantity_received     O'ZGARMAYDI (tarix — asl qabul miqdori)
          - product.stock               ↓
          - StockAdjustment (return)    yaratiladi

        Validatsiya:
          - Faqat remaining_quantity qaytarish mumkin
          - Sotilgan (quantity_received - remaining_quantity) ga tegib bo'lmaydi
        """
        if quantity <= 0:
            raise ValueError("Miqdor 0 dan katta bo'lishi kerak")
        if quantity > batch.remaining_quantity:
            sold = batch.quantity_received - batch.remaining_quantity
            raise ValueError(
                f"Faqat {batch.remaining_quantity} ta qoldiq qaytarish mumkin "
                f"({sold} ta allaqachon mijozga sotilgan)"
            )

        with transaction.atomic():
            returned_amount = Decimal(str(quantity)) * batch.cost_price

            # FAQAT remaining kamayadi — quantity_received tarix, o'zgarmaydi
            batch.remaining_quantity -= quantity
            batch.save(update_fields=['remaining_quantity'])

            batch.product.stock = F('stock') - quantity
            batch.product.save(update_fields=['stock'])

            StockAdjustment.objects.create(
                batch=batch,
                user=user,
                adjustment_type='return',
                quantity_change=-quantity,
                reason=reason or "Xarid qaytarish",
            )

            return returned_amount
