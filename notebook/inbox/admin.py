# notebook/inbox/admin.py
from django.contrib import admin
from .models import IncomingTransaction


@admin.register(IncomingTransaction)
class IncomingTransactionAdmin(admin.ModelAdmin):
    list_display = ['business', 'parsed_amount', 'status', 'source', 'matched_client', 'created_at']
    list_filter = ['business', 'status', 'source']
    search_fields = ['raw_text', 'sender_hint']
    readonly_fields = ['raw_text', 'parsed_amount', 'sender_hint', 'source', 'created_at']
