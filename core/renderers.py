import json
from rest_framework.renderers import JSONRenderer
from django.core.serializers.json import DjangoJSONEncoder


class SafeJSONRenderer(JSONRenderer):
    """
    Кастомный JSON renderer, который безопасно обрабатывает некорректные данные
    """
    
    def render(self, data, accepted_media_type=None, renderer_context=None):
        """
        Безопасно рендерит данные в JSON, заменяя некорректные символы
        """
        if data is None:
            return b''
        
        try:
            # Пытаемся сериализовать данные стандартным способом
            return super().render(data, accepted_media_type, renderer_context)
        except (UnicodeDecodeError, UnicodeEncodeError, TypeError) as e:
            # Если произошла ошибка кодировки, очищаем данные и сериализуем заново
            print(f"JSON serialization error: {e}")
            cleaned_data = self._clean_data(data)
            return json.dumps(cleaned_data, cls=DjangoJSONEncoder, ensure_ascii=False).encode('utf-8')
    
    def _clean_data(self, data):
        """
        Рекурсивно очищает данные от некорректных символов
        """
        if isinstance(data, dict):
            cleaned = {}
            for key, value in data.items():
                try:
                    cleaned_key = self._clean_value(key)
                    cleaned_value = self._clean_data(value)
                    cleaned[cleaned_key] = cleaned_value
                except Exception as e:
                    print(f"Error cleaning dict key/value: {e}")
                    cleaned[f"error_key_{id(key)}"] = "Ошибка загрузки"
            return cleaned
        
        elif isinstance(data, list):
            cleaned = []
            for item in data:
                try:
                    cleaned_item = self._clean_data(item)
                    cleaned.append(cleaned_item)
                except Exception as e:
                    print(f"Error cleaning list item: {e}")
                    cleaned.append("Ошибка загрузки")
            return cleaned
        
        else:
            return self._clean_value(data)
    
    def _clean_value(self, value):
        """
        Очищает отдельное значение от некорректных символов
        """
        if value is None:
            return None
        
        try:
            if isinstance(value, bytes):
                # Если это bytes, пытаемся декодировать
                return value.decode('utf-8', errors='replace')
            elif isinstance(value, str):
                # Если это строка, проверяем корректность
                value.encode('utf-8')  # Проверяем, что можно закодировать
                return value
            else:
                # Для других типов данных возвращаем как есть
                return value
        except (UnicodeDecodeError, UnicodeEncodeError):
            # Если произошла ошибка, заменяем некорректные символы
            if isinstance(value, bytes):
                return value.decode('utf-8', errors='replace')
            elif isinstance(value, str):
                return value.encode('utf-8', errors='replace').decode('utf-8')
            else:
                return str(value).encode('utf-8', errors='replace').decode('utf-8')
        except Exception as e:
            # Для любых других ошибок возвращаем строку с ошибкой
            print(f"Error cleaning value {type(value)}: {e}")
            return f"Ошибка загрузки ({type(value).__name__})" 