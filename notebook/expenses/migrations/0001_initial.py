# notebook/expenses/migrations/0001_initial.py
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PersonalExpense',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('category', models.CharField(
                    blank=True, default='', max_length=100,
                    verbose_name='Kategoriya (izoh)',
                    help_text="Ixtiyoriy. Masalan: Transport, Ovqat, Ko'ngil ochar",
                )),
                ('amount', models.DecimalField(decimal_places=2, max_digits=14, verbose_name="Miqdor (so'm)")),
                ('description', models.CharField(max_length=255, verbose_name='Tavsif')),
                ('date', models.DateField(verbose_name='Sana')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='personal_expenses',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Foydalanuvchi',
                )),
            ],
            options={
                'verbose_name': 'Shaxsiy chiqim',
                'verbose_name_plural': 'Shaxsiy chiqimlar',
                'ordering': ['-date', '-created_at'],
            },
        ),
    ]
