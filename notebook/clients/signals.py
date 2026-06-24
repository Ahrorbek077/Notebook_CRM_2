# notebook/clients/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Client
from notebook.activity.models import ActivityLog

# Faqat balans o'zgarganda chaqiriladigan fieldlar — bular uchun log yozmaymiz
BALANCE_ONLY_FIELDS = frozenset({'total_debt', 'advance_balance'})


@receiver(post_save, sender=Client)
def log_client_save(sender, instance, created, update_fields, **kwargs):
    # Faqat balans yangilanganda (sotuv/to'lov paytida) — log yozmaymiz
    if not created and update_fields:
        changed = frozenset(update_fields)
        if changed <= BALANCE_ONLY_FIELDS:
            return  # balans o'zgarishi — tarixga keraksiz

    ActivityLog.objects.create(
        user=getattr(instance, '_current_user', None),
        business=instance.business,
        action_type='client_create' if created else 'client_update',
        description=f"{'Yangi mijoz' if created else 'Mijoz yangilandi'}: {instance.name}",
        extra_data={
            'client_id': instance.id,
            'name':      instance.name,
            'phone':     instance.phone,
            'region':    instance.region.name if instance.region else None,
        }
    )
