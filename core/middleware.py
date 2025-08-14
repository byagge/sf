from django.shortcuts import redirect
from django.urls import reverse
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.conf import settings
from apps.users.models import User


class RoleBasedRedirectMiddleware:
    """
    Middleware для редиректа пользователей на соответствующие страницы
    на основе их ролей при посещении корневого URL (/)
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Проверяем, является ли это запрос к корневому URL
        if request.path == '/' and request.user.is_authenticated:
            # Получаем роль пользователя
            user_role = getattr(request.user, 'role', None)
            
            # Определяем URL для редиректа на основе роли
            redirect_url = self.get_redirect_url_by_role(user_role)
            
            if redirect_url and redirect_url != request.path:
                return redirect(redirect_url)
        
        response = self.get_response(request)
        return response

    def get_redirect_url_by_role(self, role):
        """
        Возвращает URL для редиректа на основе роли пользователя
        """
        if not role:
            return None
            
        role_redirects = {
            User.Role.FOUNDER: '/dashboard/',  # Учредитель -> дашборд
            User.Role.DIRECTOR: '/dashboard/',  # Директор -> дашборд
            User.Role.ADMIN: '/dashboard/',  # Администратор -> дашборд
            User.Role.ACCOUNTANT: '/dashboard/',  # Бухгалтер -> дашборд
            User.Role.MASTER: '/dashboard/',  # Мастер -> дашборд
            User.Role.WORKER: '/employee_tasks/tasks/',  # Рабочий -> задачи сотрудника
        }
        
        return role_redirects.get(role, None) 