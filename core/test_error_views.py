"""
Тестовые views для проверки работы страниц ошибок
"""
from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import permission_required


def test_400_view(request):
    """Тестовая страница для ошибки 400"""
    from .error_views import custom_400
    return custom_400(request)


def test_401_view(request):
    """Тестовая страница для ошибки 401"""
    from .error_views import custom_401
    return custom_401(request)


def test_403_view(request):
    """Тестовая страница для ошибки 403"""
    from .error_views import custom_403
    return custom_403(request)


def test_404_view(request):
    """Тестовая страница для ошибки 404"""
    from .error_views import custom_404
    return custom_404(request)


def test_500_view(request):
    """Тестовая страница для ошибки 500"""
    from .error_views import custom_500
    return custom_500(request)


def test_502_view(request):
    """Тестовая страница для ошибки 502"""
    from .error_views import custom_502
    return custom_502(request)


def test_503_view(request):
    """Тестовая страница для ошибки 503"""
    from .error_views import custom_503
    return custom_503(request)


def test_custom_error_view(request):
    """Тестовая страница для универсальной ошибки"""
    from .error_views import custom_error
    return custom_error(request, "418", "Я чайник", "Сервер отказывается варить кофе")


def test_trigger_500(request):
    """Тестовая страница для принудительного вызова ошибки 500"""
    raise Exception("Это тестовая ошибка 500")


def test_trigger_403(request):
    """Тестовая страница для принудительного вызова ошибки 403"""
    from django.core.exceptions import PermissionDenied
    raise PermissionDenied("Это тестовая ошибка 403")


def test_trigger_400(request):
    """Тестовая страница для принудительного вызова ошибки 400"""
    from django.core.exceptions import BadRequest
    raise BadRequest("Это тестовая ошибка 400") 