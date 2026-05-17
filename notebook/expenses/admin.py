# notebook/expenses/admin.py
from django.contrib import admin
from .models import PersonalExpense


@admin.register(PersonalExpense)
class PersonalExpenseAdmin(admin.ModelAdmin):
    list_display   = ('user', 'description', 'amount', 'category', 'date')
    list_filter    = ('user', 'category', 'date')
    search_fields  = ('description', 'category')
    date_hierarchy = 'date'
