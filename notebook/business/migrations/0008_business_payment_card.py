# Generated migration — payment_card_number / payment_card_holder
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('business', '0007_alter_business_webhook_token'),
    ]

    operations = [
        migrations.AddField(
            model_name='business',
            name='payment_card_number',
            field=models.CharField(
                max_length=25, blank=True, default='',
                verbose_name="To'lov kartasi raqami",
                help_text="SMS orqali qarz eslatmasida ko'rsatiladi (bo'sh bo'lsa chiqmaydi)",
            ),
        ),
        migrations.AddField(
            model_name='business',
            name='payment_card_holder',
            field=models.CharField(
                max_length=100, blank=True, default='',
                verbose_name="Karta egasi F.I.SH.",
            ),
        ),
    ]
