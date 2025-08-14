from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import json

from .models import (
    Notification, NotificationType, NotificationTemplate,
    NotificationGroup, NotificationLog
)

User = get_user_model()
logger = logging.getLogger(__name__)


class NotificationService:
    """Сервис для работы с уведомлениями"""
    
    def __init__(self):
        self.default_notification_type = None
        self._init_default_type()
    
    def _init_default_type(self):
        """Инициализация типа уведомления по умолчанию"""
        try:
            self.default_notification_type = NotificationType.objects.filter(
                is_active=True
            ).first()
        except Exception as e:
            logger.error(f"Ошибка инициализации типа уведомления: {e}")
    
    def send_notification(
        self,
        recipient: User,
        title: str,
        message: str,
        notification_type: Optional[NotificationType] = None,
        priority: str = 'medium',
        action_url: Optional[str] = None,
        action_text: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
        content_object: Optional[Any] = None
    ) -> Optional[Notification]:
        """
        Отправить уведомление пользователю
        
        Args:
            recipient: Получатель уведомления
            title: Заголовок уведомления
            message: Текст уведомления
            notification_type: Тип уведомления
            priority: Приоритет уведомления
            action_url: URL для действия
            action_text: Текст действия
            expires_at: Дата истечения
            metadata: Дополнительные данные
            content_object: Связанный объект
            
        Returns:
            Созданное уведомление или None в случае ошибки
        """
        try:
            # Проверяем настройки пользователя
            if not self._should_send_notification(recipient):
                logger.info(f"Уведомления отключены для пользователя {recipient.username}")
                return None
            
            # Используем тип по умолчанию, если не указан
            if not notification_type:
                notification_type = self.default_notification_type
            
            if not notification_type:
                logger.error("Не указан тип уведомления и нет типа по умолчанию")
                return None
            
            # Создаем уведомление
            notification = Notification.objects.create(
                recipient=recipient,
                title=title,
                message=message,
                notification_type=notification_type,
                priority=priority,
                action_url=action_url or '',
                action_text=action_text or '',
                expires_at=expires_at,
                metadata=metadata or {}
            )
            
            # Если указан связанный объект, связываем его
            if content_object:
                from django.contrib.contenttypes.models import ContentType
                notification.content_type = ContentType.objects.get_for_model(content_object)
                notification.object_id = content_object.id
                notification.save()
            
            # Отправляем уведомления по различным каналам
            self._send_email_notification(notification)
            self._send_push_notification(notification)
            self._send_sms_notification(notification)
            
            logger.info(f"Уведомление отправлено: {notification.id} для {recipient.username}")
            return notification
            
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления: {e}")
            return None
    
    def send_bulk_notifications(
        self,
        title: str,
        message: str,
        recipient_ids: List[int],
        notification_type: Optional[NotificationType] = None,
        priority: str = 'medium',
        action_url: Optional[str] = None,
        action_text: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Массовая отправка уведомлений
        
        Args:
            title: Заголовок уведомления
            message: Текст уведомления
            recipient_ids: Список ID получателей
            notification_type: Тип уведомления
            priority: Приоритет уведомления
            action_url: URL для действия
            action_text: Текст действия
            expires_at: Дата истечения
            metadata: Дополнительные данные
            
        Returns:
            Количество созданных уведомлений
        """
        created_count = 0
        
        try:
            recipients = User.objects.filter(id__in=recipient_ids)
            
            for recipient in recipients:
                notification = self.send_notification(
                    recipient=recipient,
                    title=title,
                    message=message,
                    notification_type=notification_type,
                    priority=priority,
                    action_url=action_url,
                    action_text=action_text,
                    expires_at=expires_at,
                    metadata=metadata
                )
                
                if notification:
                    created_count += 1
            
            logger.info(f"Массовая отправка завершена: {created_count} уведомлений")
            
        except Exception as e:
            logger.error(f"Ошибка массовой отправки: {e}")
        
        return created_count
    
    def send_template_notification(
        self,
        template_name: str,
        recipient: User,
        context: Dict[str, Any],
        notification_type: Optional[NotificationType] = None,
        priority: str = 'medium',
        **kwargs
    ) -> Optional[Notification]:
        """
        Отправить уведомление по шаблону
        
        Args:
            template_name: Название шаблона
            recipient: Получатель
            context: Контекст для шаблона
            notification_type: Тип уведомления
            priority: Приоритет
            **kwargs: Дополнительные параметры
            
        Returns:
            Созданное уведомление или None
        """
        try:
            template = NotificationTemplate.objects.get(
                name=template_name,
                is_active=True
            )
            
            # Рендерим шаблон
            title = template.title_template.format(**context)
            message = template.message_template.format(**context)
            
            return self.send_notification(
                recipient=recipient,
                title=title,
                message=message,
                notification_type=notification_type or template.notification_type,
                priority=priority,
                **kwargs
            )
            
        except NotificationTemplate.DoesNotExist:
            logger.error(f"Шаблон уведомления не найден: {template_name}")
            return None
        except Exception as e:
            logger.error(f"Ошибка отправки по шаблону: {e}")
            return None
    
    def send_group_notification(
        self,
        group_name: str,
        title: str,
        message: str,
        priority: str = 'medium',
        **kwargs
    ) -> int:
        """
        Отправить уведомление группе пользователей
        
        Args:
            group_name: Название группы
            title: Заголовок
            message: Текст
            priority: Приоритет
            **kwargs: Дополнительные параметры
            
        Returns:
            Количество отправленных уведомлений
        """
        try:
            group = NotificationGroup.objects.get(
                name=group_name,
                is_active=True
            )
            
            recipient_ids = list(group.recipients.values_list('id', flat=True))
            
            return self.send_bulk_notifications(
                title=title,
                message=message,
                recipient_ids=recipient_ids,
                notification_type=group.notification_type,
                priority=priority,
                **kwargs
            )
            
        except NotificationGroup.DoesNotExist:
            logger.error(f"Группа уведомлений не найдена: {group_name}")
            return 0
        except Exception as e:
            logger.error(f"Ошибка отправки группе: {e}")
            return 0
    
    def _should_send_notification(self, user: User) -> bool:
        """Проверить, следует ли отправлять уведомление пользователю"""
        try:
            preferences = NotificationPreference.objects.get(user=user)
            
            # Проверяем время тишины
            if preferences.quiet_hours_start and preferences.quiet_hours_end:
                now = timezone.now().time()
                if preferences.quiet_hours_start <= preferences.quiet_hours_end:
                    # Обычный день (например, 9:00 - 18:00)
                    if preferences.quiet_hours_start <= now <= preferences.quiet_hours_end:
                        return False
                else:
                    # Переход через полночь (например, 22:00 - 6:00)
                    if now >= preferences.quiet_hours_start or now <= preferences.quiet_hours_end:
                        return False
            
            return True
            
        except NotificationPreference.DoesNotExist:
            # Если настройки не найдены, отправляем по умолчанию
            return True
    
    def _send_email_notification(self, notification: Notification):
        """Отправить email уведомление"""
        try:
            preferences = NotificationPreference.objects.get(user=notification.recipient)
            
            if not preferences.email_notifications:
                return
            
            # Формируем email
            subject = f"Уведомление: {notification.title}"
            
            context = {
                'notification': notification,
                'user': notification.recipient
            }
            
            html_message = render_to_string(
                'notifications/email/notification.html',
                context
            )
            
            plain_message = render_to_string(
                'notifications/email/notification.txt',
                context
            )
            
            # Отправляем email
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[notification.recipient.email],
                html_message=html_message,
                fail_silently=True
            )
            
            # Логируем отправку
            NotificationLog.objects.create(
                notification=notification,
                delivery_method='email',
                delivery_status='sent'
            )
            
        except Exception as e:
            logger.error(f"Ошибка отправки email: {e}")
            # Логируем ошибку
            NotificationLog.objects.create(
                notification=notification,
                delivery_method='email',
                delivery_status='failed',
                error_message=str(e)
            )
    
    def _send_push_notification(self, notification: Notification):
        """Отправить push уведомление"""
        try:
            preferences = NotificationPreference.objects.get(user=notification.recipient)
            
            if not preferences.push_notifications:
                return
            
            # Здесь должна быть логика отправки push уведомлений
            # Например, через Firebase Cloud Messaging или Web Push API
            
            # Логируем отправку
            NotificationLog.objects.create(
                notification=notification,
                delivery_method='push',
                delivery_status='sent'
            )
            
        except Exception as e:
            logger.error(f"Ошибка отправки push: {e}")
            NotificationLog.objects.create(
                notification=notification,
                delivery_method='push',
                delivery_status='failed',
                error_message=str(e)
            )
    
    def _send_sms_notification(self, notification: Notification):
        """Отправить SMS уведомление"""
        try:
            preferences = NotificationPreference.objects.get(user=notification.recipient)
            
            if not preferences.sms_notifications:
                return
            
            # Здесь должна быть логика отправки SMS
            # Например, через внешний SMS сервис
            
            # Логируем отправку
            NotificationLog.objects.create(
                notification=notification,
                delivery_method='sms',
                delivery_status='sent'
            )
            
        except Exception as e:
            logger.error(f"Ошибка отправки SMS: {e}")
            NotificationLog.objects.create(
                notification=notification,
                delivery_method='sms',
                delivery_status='failed',
                error_message=str(e)
            )
    
    def cleanup_expired_notifications(self):
        """Очистка истекших уведомлений"""
        try:
            expired_count = Notification.objects.filter(
                expires_at__lt=timezone.now(),
                status__in=['unread', 'read']
            ).update(status='archived')
            
            logger.info(f"Архивировано {expired_count} истекших уведомлений")
            return expired_count
            
        except Exception as e:
            logger.error(f"Ошибка очистки уведомлений: {e}")
            return 0
    
    def get_notification_stats(self, user: User) -> Dict[str, Any]:
        """Получить статистику уведомлений пользователя"""
        try:
            notifications = Notification.objects.filter(recipient=user)
            
            stats = {
                'total': notifications.count(),
                'unread': notifications.filter(status='unread').count(),
                'read': notifications.filter(status='read').count(),
                'archived': notifications.filter(status='archived').count(),
                'by_type': {},
                'by_priority': {},
                'recent': []
            }
            
            # Статистика по типам
            for notification_type in NotificationType.objects.filter(is_active=True):
                count = notifications.filter(notification_type=notification_type).count()
                if count > 0:
                    stats['by_type'][notification_type.name] = count
            
            # Статистика по приоритетам
            for priority, _ in Notification.PRIORITY_CHOICES:
                count = notifications.filter(priority=priority).count()
                if count > 0:
                    stats['by_priority'][priority] = count
            
            # Последние уведомления
            stats['recent'] = list(
                notifications.select_related('notification_type')[:5].values(
                    'id', 'title', 'notification_type__name', 'created_at', 'status'
                )
            )
            
            return stats
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return {}


class NotificationTemplateRenderer:
    """Рендерер шаблонов уведомлений"""
    
    @staticmethod
    def render_template(template: NotificationTemplate, context: Dict[str, Any]) -> Dict[str, str]:
        """
        Рендерить шаблон уведомления
        
        Args:
            template: Шаблон уведомления
            context: Контекст для рендеринга
            
        Returns:
            Словарь с заголовком и сообщением
        """
        try:
            title = template.title_template.format(**context)
            message = template.message_template.format(**context)
            
            return {
                'title': title,
                'message': message
            }
            
        except KeyError as e:
            logger.error(f"Отсутствует переменная в шаблоне: {e}")
            return {
                'title': template.title_template,
                'message': template.message_template
            }
        except Exception as e:
            logger.error(f"Ошибка рендеринга шаблона: {e}")
            return {
                'title': 'Ошибка шаблона',
                'message': 'Не удалось обработать шаблон уведомления'
            }


class NotificationScheduler:
    """Планировщик уведомлений"""
    
    @staticmethod
    def schedule_notification(
        recipient: User,
        title: str,
        message: str,
        send_at: datetime,
        **kwargs
    ) -> Optional[Notification]:
        """
        Запланировать уведомление на определенное время
        
        Args:
            recipient: Получатель
            title: Заголовок
            message: Текст
            send_at: Время отправки
            **kwargs: Дополнительные параметры
            
        Returns:
            Запланированное уведомление
        """
        try:
            # Создаем уведомление с будущей датой истечения
            expires_at = send_at + timedelta(days=7)  # Истекает через неделю
            
            notification = Notification.objects.create(
                recipient=recipient,
                title=title,
                message=message,
                expires_at=expires_at,
                **kwargs
            )
            
            # Здесь можно добавить логику для Celery или другого планировщика
            # для отправки уведомления в указанное время
            
            logger.info(f"Уведомление запланировано: {notification.id} на {send_at}")
            return notification
            
        except Exception as e:
            logger.error(f"Ошибка планирования уведомления: {e}")
            return None 