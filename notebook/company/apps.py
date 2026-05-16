from django.apps import AppConfig

class CompanyConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notebook.company'
    verbose_name = 'Kompaniyalar'

    def ready(self):
        import notebook.company.signals  # noqa
