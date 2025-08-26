from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
import uuid

User = get_user_model()


class NotificationType(models.Model):
    """Типы уведомлений"""
    name = models.CharField(
        max_length=100, 
        verbose_name='Название типа'
    )
    code = models.CharField(
        max_length=50, 
        unique=True,
        verbose_name='Код типа'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Описание'
    )
    icon = models.CharField(
        max_length=50,
        blank=True,
        default='bell',
        verbose_name='Иконка'
    )
    color = models.CharField(
        max_length=20,
        blank=True,
        default='primary',
        verbose_name='Цвет'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активен'
    )
    
    class Meta:
        verbose_name = 'Тип уведомления'
        verbose_name_plural = 'Типы уведомлений'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('info', 'Информация'),
        ('warning', 'Предупреждение'),
        ('error', 'Ошибка'),
        ('success', 'Успех'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='system_notifications')
    title = models.CharField('Заголовок', max_length=255)
    message = models.TextField('Сообщение')
    notification_type = models.CharField('Тип уведомления', max_length=20, choices=NOTIFICATION_TYPES, default='info')
    is_read = models.BooleanField('Прочитано', default=False)
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    
    class Meta:
        verbose_name = 'Уведомление'
        verbose_name_plural = 'Уведомления'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.user}"
    
    def mark_as_read(self):
        """Отмечает уведомление как прочитанное"""
        self.is_read = True
        self.save()
    
    def is_expired(self):
        """Проверить, истекло ли уведомление"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    def get_priority_class(self):
        """Получить CSS класс для приоритета"""
        priority_classes = {
            'low': 'text-muted',
            'medium': 'text-primary',
            'high': 'text-warning',
            'urgent': 'text-danger',
        }
        return priority_classes.get(self.priority, 'text-primary')


class NotificationTemplate(models.Model):
    """Шаблоны уведомлений"""
    name = models.CharField(
        max_length=100,
        verbose_name='Название шаблона'
    )
    notification_type = models.ForeignKey(
        NotificationType,
        on_delete=models.CASCADE,
        verbose_name='Тип уведомления'
    )
    title_template = models.CharField(
        max_length=200,
        verbose_name='Шаблон заголовка'
    )
    message_template = models.TextField(
        verbose_name='Шаблон сообщения'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активен'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )
    
    class Meta:
        verbose_name = 'Шаблон уведомления'
        verbose_name_plural = 'Шаблоны уведомлений'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class NotificationGroup(models.Model):
    """Группы уведомлений для массовой рассылки"""
    name = models.CharField(
        max_length=100,
        verbose_name='Название группы'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Описание'
    )
    recipients = models.ManyToManyField(
        User,
        verbose_name='Получатели'
    )
    notification_type = models.ForeignKey(
        NotificationType,
        on_delete=models.CASCADE,
        verbose_name='Тип уведомления'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активна'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    
    class Meta:
        verbose_name = 'Группа уведомлений'
        verbose_name_plural = 'Группы уведомлений'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class NotificationPreference(models.Model):
    """Настройки уведомлений пользователя"""
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='notification_preferences',
        verbose_name='Пользователь'
    )
    
    # Email уведомления
    email_notifications = models.BooleanField(
        default=True,
        verbose_name='Email уведомления'
    )
    email_daily_digest = models.BooleanField(
        default=False,
        verbose_name='Ежедневный дайджест'
    )
    email_weekly_digest = models.BooleanField(
        default=False,
        verbose_name='Еженедельный дайджест'
    )
    
    # Push уведомления
    push_notifications = models.BooleanField(
        default=True,
        verbose_name='Push уведомления'
    )
    
    # SMS уведомления
    sms_notifications = models.BooleanField(
        default=False,
        verbose_name='SMS уведомления'
    )
    
    # Настройки по типам
    preferences_by_type = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Настройки по типам'
    )
    
    # Время тишины
    quiet_hours_start = models.TimeField(
        null=True,
        blank=True,
        verbose_name='Начало тихих часов'
    )
    quiet_hours_end = models.TimeField(
        null=True,
        blank=True,
        verbose_name='Конец тихих часов'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )
    
    class Meta:
        verbose_name = 'Настройка уведомлений'
        verbose_name_plural = 'Настройки уведомлений'
    
    def __str__(self):
        return f"Настройки уведомлений для {self.user.username}"


class NotificationLog(models.Model):
    """Лог отправленных уведомлений"""
    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        verbose_name='Уведомление'
    )
    sent_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата отправки'
    )
    delivery_method = models.CharField(
        max_length=20,
        verbose_name='Способ доставки'
    )
    delivery_status = models.CharField(
        max_length=20,
        verbose_name='Статус доставки'
    )
    error_message = models.TextField(
        blank=True,
        verbose_name='Сообщение об ошибке'
    )
    
    class Meta:
        verbose_name = 'Лог уведомления'
        verbose_name_plural = 'Логи уведомлений'
        ordering = ['-sent_at']
    
    def __str__(self):
        return f"Лог {self.notification.title} - {self.delivery_method}" 