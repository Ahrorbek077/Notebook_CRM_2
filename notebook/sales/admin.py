from django.contrib import admin
from .models import Sale, SaleItem, SaleReturn, SaleReturnItem

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ['id', 'client', 'total_amount', 'status', 'created_at']

admin.site.register(SaleItem)
admin.site.register(SaleReturn)
admin.site.register(SaleReturnItem)
