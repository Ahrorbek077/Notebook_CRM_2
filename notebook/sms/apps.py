# notebook/sms/apps.py
from django.apps import AppConfig


class SmsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notebook.sms'
    label = 'sms'
    verbose_name = 'SMS'
