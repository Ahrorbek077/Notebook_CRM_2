from django.apps import AppConfig

class CatalogConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notebook.catalog'
    verbose_name = 'Katalog'

    def ready(self):
        import notebook.catalog.signals  # noqa
