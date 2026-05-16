# notebook/company/migrations/0002_add_advance_balance.py
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('company', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='branch',
            name='advance_balance',
            field=models.DecimalField(
                decimal_places=2, default=0, max_digits=14,
                verbose_name="Avansimiz (ortiqcha to'lov)"
            ),
        ),
        migrations.AddField(
            model_name='company',
            name='advance_balance',
            field=models.DecimalField(
                decimal_places=2, default=0, max_digits=14,
                verbose_name="Avansimiz (ortiqcha to'lov)"
            ),
        ),
    ]
