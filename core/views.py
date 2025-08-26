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
        
        # Если пользователь аутентифицирован, выполняем редиректы/рендер на основе роли и устройства
        user_role = getattr(request.user, 'role', None)
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        is_mobile = any(m in user_agent for m in ['android', 'iphone', 'ipad', 'mobile', 'opera mini', 'blackberry', 'windows phone'])

        # Директор/Учредитель -> директорский дашборд (моб/десктоп)
        if user_role in [User.Role.FOUNDER, User.Role.DIRECTOR]:
            return redirect('/dashboard/')  # сам /dashboard/ отрендерит нужный шаблон

        # Администратор -> операционный дашборд (моб/десктоп)
        elif user_role == User.Role.ADMIN:
            return redirect('/dashboard/')

        # Бухгалтер -> финансы
        elif user_role == User.Role.ACCOUNTANT:
            return redirect('/finance/')

        # Мастер -> мастерский дашборд (моб/десктоп)
        elif user_role == User.Role.MASTER:
            return redirect('/dashboard/')

        # Рабочий -> задачи
        elif user_role == User.Role.WORKER:
            return redirect('/employee_tasks/tasks/')
        
        # Если роль не определена, показываем домашнюю страницу
        return super().dispatch(request, *args, **kwargs)

    def get_redirect_url_by_role(self, role):
        """
        Возвращает URL для редиректа на основе роли пользователя
        """
        if not role:
            return None
            
        role_redirects = {
            User.Role.FOUNDER: '/dashboard/',
            User.Role.DIRECTOR: '/dashboard/',
            User.Role.ADMIN: '/dashboard/',
            User.Role.ACCOUNTANT: '/finance/',
            User.Role.MASTER: '/dashboard/',
            User.Role.WORKER: '/employee_tasks/tasks/',
        }
        
        return role_redirects.get(role, None)