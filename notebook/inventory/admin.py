from django.contrib import admin
from .models import StockBatch, StockAdjustment

@admin.register(StockBatch)
class StockBatchAdmin(admin.ModelAdmin):
    list_display = ['product', 'branch', 'quantity_received', 'remaining_quantity', 'cost_price', 'created_at']

@admin.register(StockAdjustment)
class StockAdjustmentAdmin(admin.ModelAdmin):
    list_display = ['batch', 'adjustment_type', 'quantity_change', 'reason', 'created_at']
