from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView
from apps.users.models import User
from django.shortcuts import render
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
import json


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

def home(request):
    """Главная страница"""
    return render(request, 'home.html')

def handler404(request, exception=None):
    """Обработчик ошибки 404 - Страница не найдена"""
    response = render(request, '404.html', status=404)
    response.status_code = 404
    return response

def handler500(request):
    """Обработчик ошибки 500 - Внутренняя ошибка сервера"""
    context = {
        'timestamp': timezone.now().strftime('%Y%m%d-%H%M%S'),
    }
    response = render(request, '500.html', context, status=500)
    response.status_code = 500
    return response

def handler400(request, exception=None):
    """Обработчик ошибки 400 - Неверный запрос"""
    response = render(request, '400.html', status=400)
    response.status_code = 400
    return response

def handler401(request, exception=None):
    """Обработчик ошибки 401 - Требуется авторизация"""
    response = render(request, '401.html', status=401)
    response.status_code = 401
    return response

def handler403(request, exception=None):
    """Обработчик ошибки 403 - Доступ запрещен"""
    response = render(request, '403.html', status=403)
    response.status_code = 403
    return response

def handler_error(request, error_code=None, error_title=None, error_message=None, error_details=None):
    """Универсальный обработчик ошибок"""
    context = {
        'error_code': error_code or 'Ошибка',
        'error_title': error_title or 'Что-то пошло не так',
        'error_message': error_message or 'Произошла непредвиденная ошибка. Попробуйте обновить страницу или вернуться на главную.',
        'error_details': error_details,
    }
    return render(request, 'error.html', context)

@csrf_exempt
@require_http_methods(["GET", "POST"])
def api_test(request):
    """Тестовый API endpoint"""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            return HttpResponse(json.dumps({"status": "success", "data": data}), content_type="application/json")
        except json.JSONDecodeError:
            return HttpResponse(json.dumps({"status": "error", "message": "Invalid JSON"}), content_type="application/json", status=400)
    
    return HttpResponse(json.dumps({"status": "success", "message": "API is working"}), content_type="application/json")