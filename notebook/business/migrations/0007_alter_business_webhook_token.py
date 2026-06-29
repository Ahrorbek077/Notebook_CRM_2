# notebook/business/migrations/0007_alter_business_webhook_token.py
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('business', '0006_backfill_webhook_tokens'),
    ]

    operations = [
        migrations.AlterField(
            model_name='business',
            name='webhook_token',
            field=models.CharField(
                blank=True, max_length=40, unique=True,
                help_text='Bank SMS/bildirishnoma avtomatlashtirish (MacroDroid) uchun maxfiy kalit',
                verbose_name='Webhook token',
            ),
        ),
    ]
