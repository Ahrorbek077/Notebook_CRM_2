from django.apps import AppConfig
class ClientsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notebook.clients'
    verbose_name = 'Mijozlar'
    def ready(self):
        import notebook.clients.signals  # noqa
