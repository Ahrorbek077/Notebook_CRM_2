from django.contrib import admin
from .models import Payment, PaymentRefund

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['client', 'amount', 'refunded_amount', 'is_cancelled', 'created_at']

@admin.register(PaymentRefund)
class PaymentRefundAdmin(admin.ModelAdmin):
    list_display = ['payment', 'amount', 'reason', 'created_at']
