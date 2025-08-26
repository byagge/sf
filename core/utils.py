from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)


def is_mobile_device(request):
    """
    Определяет, является ли устройство мобильным на основе User-Agent
    
    Args:
        request: Django request объект
        
    Returns:
        bool: True если устройство мобильное, False если десктопное
    """
    user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
    
    # Ключевые слова для определения мобильных устройств
    mobile_keywords = [
        'mobile', 'android', 'iphone', 'ipad', 'ipod',
        'windows phone', 'blackberry', 'opera mini', 'mobile safari',
        'webos', 'symbian', 'kindle', 'nokia', 'lg', 'samsung'
    ]
    
    # Проверяем наличие мобильных ключевых слов в User-Agent
    return any(keyword in user_agent for keyword in mobile_keywords)


def custom_exception_handler(exc, context):
    """
    Кастомный обработчик исключений для REST Framework
    """
    # Сначала вызываем стандартный обработчик
    response = exception_handler(exc, context)
    
    if response is not None:
        # Если стандартный обработчик вернул ответ, логируем ошибку
        logger.error(f"REST Framework exception: {exc} in {context}")
        return response
    
    # Если стандартный обработчик не смог обработать исключение
    logger.error(f"Unhandled exception: {exc} in {context}")
    
    # Возвращаем стандартную ошибку сервера
    return Response(
        {
            'error': 'Внутренняя ошибка сервера',
            'detail': 'Произошла непредвиденная ошибка при обработке запроса'
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR
    ) 