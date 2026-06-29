# notebook/business/migrations/0006_backfill_webhook_tokens.py
import secrets
from django.db import migrations


def backfill(apps, schema_editor):
    Business = apps.get_model('business', 'Business')
    for biz in Business.objects.filter(webhook_token__isnull=True):
        biz.webhook_token = secrets.token_urlsafe(24)
        biz.save(update_fields=['webhook_token'])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('business', '0005_business_webhook_token'),
    ]

    operations = [
        migrations.RunPython(backfill, noop_reverse),
    ]
