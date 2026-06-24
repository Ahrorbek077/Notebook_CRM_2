from django.contrib import admin
from .models import Client, Region

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ['name', 'business', 'phone', 'region', 'total_debt', 'advance_balance', 'is_active']
    list_filter = ['business', 'is_active']

@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ['name', 'business', 'order', 'is_active']
    list_filter = ['business']
