# notebook/business/migrations/0004_backfill_containers.py
from django.db import migrations


def backfill(apps, schema_editor):
    Business = apps.get_model('business', 'Business')
    ContainerType = apps.get_model('containers', 'ContainerType')

    business = Business.objects.filter(name="Asosiy biznes").first()
    if business is None:
        business = Business.objects.order_by('id').first()
    if business is None:
        return

    ContainerType.objects.filter(business__isnull=True).update(business=business)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('business', '0003_backfill_more_models'),
        ('containers', '0002_containertype_business_alter_containertype_name_and_more'),
    ]

    operations = [
        migrations.RunPython(backfill, noop_reverse),
    ]
