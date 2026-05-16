from django.contrib import admin
from .models import Company, Branch, BranchPayment

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'total_debt', 'is_active', 'created_at']

@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ['name', 'company', 'total_debt', 'is_active']

@admin.register(BranchPayment)
class BranchPaymentAdmin(admin.ModelAdmin):
    list_display = ['branch', 'amount', 'payment_type', 'created_at']
