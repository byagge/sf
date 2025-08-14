from django.apps import AppConfig


class WorkshopsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.operations.workshops'
    label = 'operations_workshops'

    def ready(self):
        import apps.operations.workshops.signals
