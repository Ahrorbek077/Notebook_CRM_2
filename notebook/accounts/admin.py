from django.contrib import admin
from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):

    list_display = ("username", "email", "role", "business", "is_active")

    list_filter = ("role", "business")

    search_fields = ("username", "email")