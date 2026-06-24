# notebook/business/migrations/0002_backfill_default_business.py
"""
MUHIM MIGRATSIYA — eski (multi-biznesdan oldingi) ma'lumotlarni saqlab qolish.

Bu migratsiya:
  1. "Asosiy biznes" nomli bitta Business yaratadi (agar hali bo'lmasa).
  2. Mavjud superadmin foydalanuvchini shu biznesning egasi qilib belgilaydi.
  3. business=NULL bo'lgan BARCHA User, Region, Client, ActivityLog
     yozuvlarini shu "Asosiy biznes"ga biriktiradi.

Natijada: hech qanday mavjud ma'lumot yo'qolmaydi yoki ko'rinmay qolmaydi —
hammasi avtomatik ravishda bitta (hozirgi) biznesga tushadi. Keyin
superadmin "Bizneslar" sahifasidan ukasi uchun YANGI biznes yaratib,
uning xodimlarini o'sha yangi biznesga o'tkazishi mumkin.
"""
from django.db import migrations


def backfill(apps, schema_editor):
    Business = apps.get_model('business', 'Business')
    User = apps.get_model('accounts', 'User')
    Region = apps.get_model('clients', 'Region')
    Client = apps.get_model('clients', 'Client')
    ActivityLog = apps.get_model('activity', 'ActivityLog')

    business = Business.objects.filter(name="Asosiy biznes").first()
    if business is None:
        owner = User.objects.filter(role='superadmin').order_by('id').first()
        business = Business.objects.create(name="Asosiy biznes", owner=owner)

    User.objects.filter(business__isnull=True).update(business=business)
    Region.objects.filter(business__isnull=True).update(business=business)
    Client.objects.filter(business__isnull=True).update(business=business)
    ActivityLog.objects.filter(business__isnull=True).update(business=business)


def noop_reverse(apps, schema_editor):
    # Orqaga qaytarish ma'noga ega emas — business maydonlari shunchaki NULL
    # bo'lib qoladi (modelda null=True), ma'lumot yo'qolmaydi.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('business', '0001_initial'),
        ('accounts', '0002_user_business'),
        ('clients', '0003_client_business_region_business_alter_region_name_and_more'),
        ('activity', '0002_activitylog_business'),
    ]

    operations = [
        migrations.RunPython(backfill, noop_reverse),
    ]
