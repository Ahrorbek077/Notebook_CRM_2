# notebook/inventory/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import StockBatch, StockAdjustment
from notebook.activity.models import ActivityLog


@receiver(post_save, sender=StockBatch)
def log_stock_add(sender, instance, created, **kwargs):
    if not created:
        return
    # product allaqachon xotirada bo'lishi mumkin emas (signal ichida),
    # lekin product_id bilan description yozishdan qochamiz — product.name kerak.
    # Bu bitta qo'shimcha query, lekin faqat yangi batch yaratilganda — maqbul.
    product_name = instance.product.name  # 1 query, faqat create da
    ActivityLog.objects.create(
        user=instance.created_by,
        business=instance.product.business,
        action_type='stock_add',
        description=f"{product_name} — {instance.quantity_received} ta kirim @ {instance.cost_price}",
        extra_data={
            'batch_id':     instance.id,
            'product_id':   instance.product_id,
            'product':      product_name,
            'unit_label':   instance.product.get_unit_type_display(),
            # ── Decimal → str: JSONField xom Decimal'ni serialize qilolmaydi ──
            'quantity':     str(instance.quantity_received),
            'cost_price':   str(instance.cost_price),
            'selling_price':str(instance.selling_price),
            'branch':       str(instance.branch) if instance.branch else None,
        }
    )


@receiver(post_save, sender=StockAdjustment)
def log_stock_adjust(sender, instance, created, **kwargs):
    if not created or instance.adjustment_type == 'return':
        return
    # batch.product — ikki qadam chuqurlik, select_related yo'q
    # Lekin bu faqat manual adjustment da chaqiriladi — production da kam bo'ladi
    batch = instance.batch
    product_name = batch.product.name  # 1 query
    ActivityLog.objects.create(
        user=instance.user,
        business=batch.product.business,
        action_type='stock_adjust',
        description=f"{product_name} — batch #{batch.id} tuzatildi",
        extra_data={
            'batch_id':        batch.id,
            'product':         product_name,
            'unit_label':      batch.product.get_unit_type_display(),
            'adjustment_type': instance.adjustment_type,
            # ── Decimal → str: JSONField xom Decimal'ni serialize qilolmaydi ──
            'quantity_change': str(instance.quantity_change) if instance.quantity_change is not None else None,
            'reason':          instance.reason,
        }
    )