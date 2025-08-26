"""
Views для обработки HTTP ошибок
"""
from django.shortcuts import render
from django.http import HttpResponse


def custom_400(request, exception=None):
    """Обработчик ошибки 400 - Неверный запрос"""
    return render(request, 'errors/400.html', status=400)


def custom_401(request, exception=None):
    """Обработчик ошибки 401 - Требуется авторизация"""
    return render(request, 'errors/401.html', status=401)


def custom_403(request, exception=None):
    """Обработчик ошибки 403 - Доступ запрещен"""
    return render(request, 'errors/403.html', status=403)


def custom_404(request, exception=None):
    """Обработчик ошибки 404 - Страница не найдена"""
    return render(request, 'errors/404.html', status=404)


def custom_500(request, exception=None):
    """Обработчик ошибки 500 - Внутренняя ошибка сервера"""
    return render(request, 'errors/500.html', status=500)


def custom_502(request, exception=None):
    """Обработчик ошибки 502 - Плохой шлюз"""
    return render(request, 'errors/502.html', status=502)


def custom_503(request, exception=None):
    """Обработчик ошибки 503 - Сервис недоступен"""
    return render(request, 'errors/503.html', status=503)


def custom_error(request, error_code=None, error_title=None, error_message=None):
    """Универсальный обработчик ошибок с параметрами"""
    context = {
        'error_code': error_code or 'Ошибка',
        'error_title': error_title or 'Произошла ошибка',
        'error_message': error_message or 'Что-то пошло не так. Попробуйте обновить страницу или вернуться на главную'
    }
    return render(request, 'errors/error.html', context, status=400) 