# notebook/inbox/apps.py
from django.apps import AppConfig


class InboxConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notebook.inbox'
    label = 'inbox'
    verbose_name = "Kelgan to'lovlar"
