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

    # Soft-delete (is_active=False qilingan) holatni alohida aniqlaymiz —
    # aks holda "o'chirildi" amali ham "yangilandi" deb yozilib qolardi.
    is_soft_delete = (not created) and update_fields == frozenset({'is_active'}) and not instance.is_active

    if created:
        action_type, label = 'client_create', 'Yangi mijoz'
    elif is_soft_delete:
        action_type, label = 'client_delete', "Mijoz o'chirildi"
    else:
        action_type, label = 'client_update', 'Mijoz yangilandi'

    ActivityLog.objects.create(
        user=getattr(instance, '_current_user', None),
        business=instance.business,
        action_type=action_type,
        description=f"{label}: {instance.name}",
        extra_data={
            'client_id': instance.id,
            'name':      instance.name,
            'phone':     instance.phone,
            'region':    instance.region.name if instance.region else None,
        }
    )