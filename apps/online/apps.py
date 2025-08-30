from django.apps import AppConfig


class OnlineConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.online'
    verbose_name = 'Онлайн пользователи'
    
    def ready(self):
        # Импортируем сигналы при запуске приложения
        try:
            import apps.online.signals
        except ImportError:
            pass
