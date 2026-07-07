# notebook/ocr/apps.py
from django.apps import AppConfig


class OcrConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notebook.ocr'
    verbose_name = "Chek OCR (xarid)"
