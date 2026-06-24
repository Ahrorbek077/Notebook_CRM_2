# notebook/business/migrations/0003_backfill_more_models.py
"""
Birinchi backfill (0002) faqat User/Region/Client/ActivityLog uchun edi.
Bu migratsiya endi Mahsulot/Kategoriya/Kompaniya/Ombor/Sotuv/To'lov
modellarini ham xuddi shu "Asosiy biznes"ga biriktiradi — shu bilan
HECH QANDAY mavjud mahsulot, sotuv yoki to'lov ko'rinmay qolmaydi.
"""
from django.db import migrations


def backfill(apps, schema_editor):
    Business = apps.get_model('business', 'Business')
    Category = apps.get_model('catalog', 'Category')
    Product = apps.get_model('catalog', 'Product')
    Company = apps.get_model('company', 'Company')
    StockBatch = apps.get_model('inventory', 'StockBatch')
    Sale = apps.get_model('sales', 'Sale')
    Payment = apps.get_model('payments', 'Payment')

    business = Business.objects.filter(name="Asosiy biznes").first()
    if business is None:
        # 0002 ishlamagan / topilmagan holat uchun ehtiyot chorasi
        business = Business.objects.order_by('id').first()
    if business is None:
        return

    Category.objects.filter(business__isnull=True).update(business=business)
    Product.objects.filter(business__isnull=True).update(business=business)
    Company.objects.filter(business__isnull=True).update(business=business)
    StockBatch.objects.filter(business__isnull=True).update(business=business)
    Sale.objects.filter(business__isnull=True).update(business=business)
    Payment.objects.filter(business__isnull=True).update(business=business)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('business', '0002_backfill_default_business'),
        ('catalog', '0005_category_business_product_business_and_more'),
        ('company', '0003_company_business'),
        ('inventory', '0003_stockbatch_business'),
        ('sales', '0003_sale_business'),
        ('payments', '0002_payment_business'),
    ]

    operations = [
        migrations.RunPython(backfill, noop_reverse),
    ]
