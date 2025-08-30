import openai
import os
from django.conf import settings
from django.utils import timezone
from .models import AIUserSettings, ChatMessage, SupportChat
import logging

logger = logging.getLogger(__name__)

class AISupportService:
    """Сервис для работы с ИИ в поддержке"""
    
    def __init__(self):
        self.api_key = getattr(settings, 'OPENAI_API_KEY', None)
        if self.api_key:
            openai.api_key = self.api_key
    
    def is_available(self):
        """Проверяет доступность ИИ"""
        return bool(self.api_key)
    
    def get_user_ai_settings(self, user):
        """Получает настройки ИИ для пользователя"""
        try:
            settings_obj, created = AIUserSettings.objects.get_or_create(
                user=user,
                defaults={
                    'ai_enabled': True,
                    'ai_model': 'gpt-3.5-turbo',
                    'max_tokens': 1000,
                    'temperature': 0.7
                }
            )
            return settings_obj
        except Exception as e:
            logger.error(f"Ошибка получения настроек ИИ для пользователя {user.username}: {e}")
            return None
    
    def is_ai_enabled_for_user(self, user):
        """Проверяет, включен ли ИИ для пользователя"""
        settings_obj = self.get_user_ai_settings(user)
        return settings_obj and settings_obj.ai_enabled if settings_obj else False
    
    def generate_ai_response(self, user, chat, user_message):
        """Генерирует ответ ИИ на сообщение пользователя"""
        if not self.is_available():
            return "Извините, ИИ временно недоступен. Обратитесь к администратору."
        
        if not self.is_ai_enabled_for_user(user):
            return "ИИ отключен для вашего аккаунта. Обратитесь к администратору для включения."
        
        try:
            # Получаем настройки ИИ для пользователя
            ai_settings = self.get_user_ai_settings(user)
            if not ai_settings:
                return "Ошибка получения настроек ИИ. Обратитесь к администратору."
            
            # Формируем контекст из истории чата
            chat_history = self._get_chat_context(chat, user_message)
            
            # Генерируем ответ через OpenAI
            response = openai.ChatCompletion.create(
                model=ai_settings.ai_model,
                messages=chat_history,
                max_tokens=ai_settings.max_tokens,
                temperature=ai_settings.temperature
            )
            
            ai_response = response.choices[0].message.content.strip()
            return ai_response
            
        except openai.error.RateLimitError:
            return "Превышен лимит запросов к ИИ. Попробуйте позже."
        except openai.error.APIError as e:
            logger.error(f"Ошибка API OpenAI: {e}")
            return "Ошибка работы с ИИ. Попробуйте позже."
        except Exception as e:
            logger.error(f"Ошибка генерации ответа ИИ: {e}")
            return "Произошла ошибка. Обратитесь к администратору."
    
    def _get_chat_context(self, chat, current_message):
        """Формирует контекст для ИИ из истории чата"""
        # Системный промпт
        system_prompt = """Ты - помощник службы поддержки умной фабрики. 
        Твоя задача - помогать пользователям с вопросами по работе системы.
        Отвечай кратко, по делу и дружелюбно.
        Если не можешь помочь - предложи обратиться к администратору."""
        
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # Получаем последние 10 сообщений для контекста
        recent_messages = chat.messages.order_by('-created_at')[:10]
        
        for msg in reversed(recent_messages):
            if msg.message_type == 'user':
                messages.append({"role": "user", "content": msg.content})
            elif msg.message_type == 'ai':
                messages.append({"role": "assistant", "content": msg.content})
            elif msg.message_type == 'admin':
                messages.append({"role": "user", "content": f"Администратор: {msg.content}"})
        
        # Добавляем текущее сообщение пользователя
        messages.append({"role": "user", "content": current_message})
        
        return messages
    
    def create_ai_message(self, chat, content):
        """Создает сообщение от ИИ в чате"""
        try:
            message = ChatMessage.objects.create(
                chat=chat,
                message_type='ai',
                content=content
            )
            # Обновляем время последнего обновления чата
            chat.updated_at = timezone.now()
            chat.save()
            return message
        except Exception as e:
            logger.error(f"Ошибка создания сообщения ИИ: {e}")
            return None
    
    def toggle_ai_for_user(self, user, enabled=True):
        """Включает/выключает ИИ для пользователя"""
        try:
            settings_obj, created = AIUserSettings.objects.get_or_create(
                user=user,
                defaults={'ai_enabled': enabled}
            )
            if not created:
                settings_obj.ai_enabled = enabled
                settings_obj.save()
            return True
        except Exception as e:
            logger.error(f"Ошибка изменения настроек ИИ для пользователя {user.username}: {e}")
            return False 