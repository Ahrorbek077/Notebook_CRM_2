# notebook/business/migrations/0005_business_webhook_token.py
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('business', '0004_backfill_containers'),
    ]

    operations = [
        migrations.AddField(
            model_name='business',
            name='webhook_token',
            field=models.CharField(
                blank=True, null=True, max_length=40, unique=True, default=None,
                help_text='Bank SMS/bildirishnoma avtomatlashtirish (MacroDroid) uchun maxfiy kalit',
                verbose_name='Webhook token',
            ),
        ),
    ]
