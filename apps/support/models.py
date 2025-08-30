from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class SupportChat(models.Model):
    """Модель чата поддержки"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='support_chats')
    title = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'Чат поддержки'
        verbose_name_plural = 'Чаты поддержки'
    
    def __str__(self):
        return f"Чат {self.user.username} - {self.title or 'Без названия'}"

class ChatMessage(models.Model):
    """Модель сообщения в чате"""
    MESSAGE_TYPES = [
        ('user', 'Пользователь'),
        ('ai', 'ИИ'),
        ('admin', 'Администратор'),
    ]
    
    chat = models.ForeignKey(SupportChat, on_delete=models.CASCADE, related_name='messages')
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
        verbose_name = 'Сообщение чата'
        verbose_name_plural = 'Сообщения чата'
    
    def __str__(self):
        return f"{self.get_message_type_display()}: {self.content[:50]}..."

class AIUserSettings(models.Model):
    """Настройки ИИ для пользователя"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='ai_settings')
    ai_enabled = models.BooleanField(default=True, verbose_name='ИИ включен')
    ai_model = models.CharField(max_length=50, default='gpt-3.5-turbo', verbose_name='Модель ИИ')
    max_tokens = models.IntegerField(default=1000, verbose_name='Максимум токенов')
    temperature = models.FloatField(default=0.7, verbose_name='Температура')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Настройки ИИ пользователя'
        verbose_name_plural = 'Настройки ИИ пользователей'
    
    def __str__(self):
        status = "включен" if self.ai_enabled else "отключен"
        return f"ИИ для {self.user.username} - {status}"

class SupportCategory(models.Model):
    """Категории обращений в поддержку"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Категория поддержки'
        verbose_name_plural = 'Категории поддержки'
    
    def __str__(self):
        return self.name

class SupportTicket(models.Model):
    """Тикеты поддержки для администраторов"""
    PRIORITY_CHOICES = [
        ('low', 'Низкий'),
        ('medium', 'Средний'),
        ('high', 'Высокий'),
        ('urgent', 'Срочный'),
    ]
    
    STATUS_CHOICES = [
        ('open', 'Открыт'),
        ('in_progress', 'В работе'),
        ('resolved', 'Решен'),
        ('closed', 'Закрыт'),
    ]
    
    chat = models.OneToOneField(SupportChat, on_delete=models.CASCADE, related_name='ticket')
    category = models.ForeignKey(SupportCategory, on_delete=models.SET_NULL, null=True, blank=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='open')
    assigned_admin = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                     related_name='assigned_tickets')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Тикет поддержки'
        verbose_name_plural = 'Тикеты поддержки'
    
    def __str__(self):
        return f"Тикет #{self.id} - {self.chat.user.username} ({self.get_status_display()})"
