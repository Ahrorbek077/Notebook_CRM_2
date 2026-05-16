from django.contrib import admin
from .models import ActivityLog

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display  = ['created_at', 'user', 'action_type', 'description']
    list_filter   = ['action_type']
    search_fields = ['description', 'user__username']
    readonly_fields = ['created_at', 'extra_data']
