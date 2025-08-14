from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView
from apps.users.models import User


class HomeView(TemplateView):
    """
    View для обработки корневого URL (/)
    Проверяет аутентификацию и редиректит на соответствующие страницы
    """
    template_name = 'home.html'

    def dispatch(self, request, *args, **kwargs):
        # Если пользователь не аутентифицирован, редиректим на страницу входа
        if not request.user.is_authenticated:
            return redirect('/accounts/login/')
        
        # Если пользователь аутентифицирован, редиректим на основе роли
        user_role = getattr(request.user, 'role', None)
        redirect_url = self.get_redirect_url_by_role(user_role)
        
        if redirect_url and redirect_url != request.path:
            return redirect(redirect_url)
        
        # Если роль не определена, показываем домашнюю страницу
        return super().dispatch(request, *args, **kwargs)

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