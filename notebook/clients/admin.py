from django.contrib import admin
from .models import Client, Region

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone', 'region', 'total_debt', 'advance_balance', 'is_active']

@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ['name', 'order', 'is_active']
