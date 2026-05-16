from django.apps import AppConfig

class InventoryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notebook.inventory'
    verbose_name = 'Ombor'

    def ready(self):
        import notebook.inventory.signals  # noqa
