from django.apps import AppConfig


class DashboardConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.odashboard'
    label = 'operations_dashboard'  # Уникальный label для устранения конфликта
