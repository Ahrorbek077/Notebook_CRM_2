# notebook/sms/admin.py
from django.contrib import admin
from .models import SmsLog


@admin.register(SmsLog)
class SmsLogAdmin(admin.ModelAdmin):
    list_display = ['phone', 'client', 'business', 'status', 'created_at']
    list_filter = ['status', 'business']
    search_fields = ['phone', 'client__name']
    readonly_fields = ['business', 'client', 'phone', 'message', 'status', 'eskiz_id', 'error', 'sent_by', 'created_at']
