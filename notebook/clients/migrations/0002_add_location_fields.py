# notebook/clients/migrations/0002_add_location_fields.py
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='latitude',
            field=models.DecimalField(
                max_digits=9, decimal_places=6,
                null=True, blank=True,
                verbose_name="Kenglik (lat)"
            ),
        ),
        migrations.AddField(
            model_name='client',
            name='longitude',
            field=models.DecimalField(
                max_digits=9, decimal_places=6,
                null=True, blank=True,
                verbose_name="Uzunlik (lng)"
            ),
        ),
    ]
