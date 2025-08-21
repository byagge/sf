import logging
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.conf import settings

logger = logging.getLogger(__name__)

class ErrorHandlingMiddleware:
    """Middleware для обработки ошибок и их логирования"""
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_exception(self, request, exception):
        """Обработка исключений"""
        # Логируем ошибку
        logger.error(
            f"Exception in {request.path}: {str(exception)}",
            extra={
                'request': request,
                'exception': exception,
                'timestamp': timezone.now().isoformat(),
            }
        )
        
        # Определяем тип ошибки и возвращаем соответствующую страницу
        if hasattr(exception, 'status_code'):
            status_code = exception.status_code
        else:
            status_code = 500
            
        # Выбираем шаблон в зависимости от статуса
        if status_code == 404:
            template = '404.html'
        elif status_code == 500:
            template = '500.html'
        elif status_code == 400:
            template = '400.html'
        elif status_code == 401:
            template = '401.html'
        elif status_code == 403:
            template = '403.html'
        else:
            template = 'error.html'
            
        context = {
            'error_code': status_code,
            'error_title': getattr(exception, 'default_detail', 'Ошибка'),
            'error_message': str(exception),
            'timestamp': timezone.now().strftime('%Y%m%d-%H%M%S'),
        }
        
        return render(request, template, context, status=status_code)

class RequestLoggingMiddleware:
    """Middleware для логирования запросов"""
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Логируем входящий запрос
        logger.info(
            f"Request: {request.method} {request.path}",
            extra={
                'request': request,
                'timestamp': timezone.now().isoformat(),
            }
        )
        
        response = self.get_response(request)
        
        # Логируем ответ
        logger.info(
            f"Response: {response.status_code} for {request.method} {request.path}",
            extra={
                'request': request,
                'response': response,
                'timestamp': timezone.now().isoformat(),
            }
        )
        
        return response

class SecurityHeadersMiddleware:
    """Middleware для добавления заголовков безопасности"""
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Добавляем заголовки безопасности
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        
        # Добавляем заголовок для PWA
        response['X-Theme-Color'] = '#2563eb'
        
        return response 