# notebook/catalog/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Product
from notebook.activity.models import ActivityLog

# Faqat stock o'zgarganda — log yozmaymiz (sotuv/xarid/qaytarish paytida)
STOCK_ONLY_FIELDS = frozenset({'stock'})


@receiver(post_save, sender=Product)
def log_product_save(sender, instance, created, update_fields, **kwargs):
    # Faqat stock yangilanganda (sotuv/xarid paytida) — log yozmaymiz
    if not created and update_fields:
        changed = frozenset(update_fields)
        if changed <= STOCK_ONLY_FIELDS:
            return

    ActivityLog.objects.create(
        user=getattr(instance, '_current_user', None),
        business=instance.business,
        action_type='product_create' if created else 'product_update',
        description=f"{'Yangi mahsulot' if created else 'Mahsulot yangilandi'}: {instance.name}",
        extra_data={
            'product_id': instance.id,
            'name':       instance.name,
            'price':      str(instance.price),
            'stock':      str(instance.stock),
            'unit_label': instance.get_unit_type_display(),
        }
    )