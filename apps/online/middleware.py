from django.utils import timezone
from .models import UserActivity

class UserActivityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Обрабатываем запрос
        response = self.get_response(request)
        
        # Обновляем активность пользователя, если он аутентифицирован
        if request.user.is_authenticated:
            try:
                UserActivity.update_user_activity(request.user)
            except Exception:
                # Игнорируем ошибки при обновлении активности
                pass
        
        return response 