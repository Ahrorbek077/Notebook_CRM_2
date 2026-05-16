# notebook/inventory/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import StockBatch, StockAdjustment
from notebook.activity.models import ActivityLog


@receiver(post_save, sender=StockBatch)
def log_stock_add(sender, instance, created, **kwargs):
    if not created:
        return
    ActivityLog.objects.create(
        user=instance.created_by,
        action_type='stock_add',
        description=f"{instance.product.name} — {instance.quantity_received} ta kirim @ {instance.cost_price}",
        extra_data={
            'batch_id':     instance.id,
            'product_id':   instance.product_id,
            'product':      instance.product.name,
            'quantity':     instance.quantity_received,
            'cost_price':   str(instance.cost_price),
            'selling_price':str(instance.selling_price),
            'branch':       str(instance.branch) if instance.branch else None,
        }
    )


@receiver(post_save, sender=StockAdjustment)
def log_stock_adjust(sender, instance, created, **kwargs):
    if not created or instance.adjustment_type == 'return':
        return
    batch = instance.batch
    ActivityLog.objects.create(
        user=instance.user,
        action_type='stock_adjust' if instance.adjustment_type != 'return' else 'stock_return',
        description=f"{batch.product.name} — batch #{batch.id} tuzatildi",
        extra_data={
            'batch_id':        batch.id,
            'product':         batch.product.name,
            'adjustment_type': instance.adjustment_type,
            'quantity_change': instance.quantity_change,
            'reason':          instance.reason,
        }
    )
