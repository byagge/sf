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