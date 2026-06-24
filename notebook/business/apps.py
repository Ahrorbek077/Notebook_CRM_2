# notebook/business/apps.py
from django.apps import AppConfig


class BusinessConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notebook.business'
    label = 'business'
    verbose_name = 'Biznes'
