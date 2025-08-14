from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from datetime import datetime, timedelta
import json

from .models import (
    Notification, NotificationType, NotificationTemplate,
    NotificationGroup, NotificationPreference, NotificationLog
)
from .utils import NotificationService

User = get_user_model()


class NotificationModelsTest(TestCase):
    """Тесты для моделей уведомлений"""
    
    def setUp(self):
        """Настройка тестовых данных"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.notification_type = NotificationType.objects.create(
            name='Тестовое уведомление',
            code='test_notification',
            description='Тестовый тип уведомления',
            icon='bell',
            color='primary'
        )
    
    def test_notification_type_creation(self):
        """Тест создания типа уведомления"""
        self.assertEqual(self.notification_type.name, 'Тестовое уведомление')
        self.assertEqual(self.notification_type.code, 'test_notification')
        self.assertTrue(self.notification_type.is_active)
    
    def test_notification_creation(self):
        """Тест создания уведомления"""
        notification = Notification.objects.create(
            recipient=self.user,
            title='Тестовое уведомление',
            message='Это тестовое сообщение',
            notification_type=self.notification_type,
            priority='high'
        )
        
        self.assertEqual(notification.recipient, self.user)
        self.assertEqual(notification.title, 'Тестовое уведомление')
        self.assertEqual(notification.status, 'unread')
        self.assertEqual(notification.priority, 'high')
    
    def test_notification_mark_as_read(self):
        """Тест отметки уведомления как прочитанного"""
        notification = Notification.objects.create(
            recipient=self.user,
            title='Тестовое уведомление',
            message='Это тестовое сообщение',
            notification_type=self.notification_type
        )
        
        self.assertEqual(notification.status, 'unread')
        self.assertIsNone(notification.read_at)
        
        notification.mark_as_read()
        
        self.assertEqual(notification.status, 'read')
        self.assertIsNotNone(notification.read_at)
    
    def test_notification_expiry(self):
        """Тест истечения уведомления"""
        # Уведомление без даты истечения
        notification1 = Notification.objects.create(
            recipient=self.user,
            title='Уведомление без истечения',
            message='Тест',
            notification_type=self.notification_type
        )
        
        self.assertFalse(notification1.is_expired())
        
        # Уведомление с истекшей датой
        expired_date = timezone.now() - timedelta(days=1)
        notification2 = Notification.objects.create(
            recipient=self.user,
            title='Истекшее уведомление',
            message='Тест',
            notification_type=self.notification_type,
            expires_at=expired_date
        )
        
        self.assertTrue(notification2.is_expired())
    
    def test_notification_priority_class(self):
        """Тест CSS классов приоритета"""
        notification = Notification.objects.create(
            recipient=self.user,
            title='Тест',
            message='Тест',
            notification_type=self.notification_type,
            priority='urgent'
        )
        
        self.assertEqual(notification.get_priority_class(), 'text-danger')
    
    def test_notification_template_creation(self):
        """Тест создания шаблона уведомления"""
        template = NotificationTemplate.objects.create(
            name='Тестовый шаблон',
            notification_type=self.notification_type,
            title_template='Уведомление для {user}',
            message_template='Привет, {user}! У вас {count} новых сообщений.'
        )
        
        self.assertEqual(template.name, 'Тестовый шаблон')
        self.assertEqual(template.notification_type, self.notification_type)
    
    def test_notification_group_creation(self):
        """Тест создания группы уведомлений"""
        group = NotificationGroup.objects.create(
            name='Тестовая группа',
            description='Описание тестовой группы',
            notification_type=self.notification_type
        )
        
        group.recipients.add(self.user)
        
        self.assertEqual(group.name, 'Тестовая группа')
        self.assertEqual(group.recipients.count(), 1)
        self.assertIn(self.user, group.recipients.all())
    
    def test_notification_preference_creation(self):
        """Тест создания настроек уведомлений"""
        preferences = NotificationPreference.objects.create(
            user=self.user,
            email_notifications=True,
            push_notifications=False,
            sms_notifications=False
        )
        
        self.assertEqual(preferences.user, self.user)
        self.assertTrue(preferences.email_notifications)
        self.assertFalse(preferences.push_notifications)
    
    def test_notification_log_creation(self):
        """Тест создания лога уведомления"""
        notification = Notification.objects.create(
            recipient=self.user,
            title='Тест',
            message='Тест',
            notification_type=self.notification_type
        )
        
        log = NotificationLog.objects.create(
            notification=notification,
            delivery_method='email',
            delivery_status='sent'
        )
        
        self.assertEqual(log.notification, notification)
        self.assertEqual(log.delivery_method, 'email')
        self.assertEqual(log.delivery_status, 'sent')


class NotificationViewsTest(TestCase):
    """Тесты для Django представлений"""
    
    def setUp(self):
        """Настройка тестовых данных"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.notification_type = NotificationType.objects.create(
            name='Тестовое уведомление',
            code='test_notification'
        )
        
        self.notification = Notification.objects.create(
            recipient=self.user,
            title='Тестовое уведомление',
            message='Это тестовое сообщение',
            notification_type=self.notification_type
        )
    
    def test_notification_list_view_authenticated(self):
        """Тест списка уведомлений для авторизованного пользователя"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('notifications:list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('notifications', response.context)
        self.assertIn(self.notification, response.context['notifications'])
    
    def test_notification_list_view_unauthenticated(self):
        """Тест списка уведомлений для неавторизованного пользователя"""
        response = self.client.get(reverse('notifications:list'))
        
        # Должен перенаправить на страницу входа
        self.assertEqual(response.status_code, 302)
    
    def test_notification_detail_view(self):
        """Тест детального представления уведомления"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(
            reverse('notifications:detail', kwargs={'pk': self.notification.pk})
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['notification'], self.notification)
    
    def test_notification_detail_view_wrong_user(self):
        """Тест доступа к уведомлению другого пользователя"""
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )
        
        self.client.login(username='otheruser', password='testpass123')
        response = self.client.get(
            reverse('notifications:detail', kwargs={'pk': self.notification.pk})
        )
        
        # Должен вернуть 404, так как уведомление принадлежит другому пользователю
        self.assertEqual(response.status_code, 404)
    
    def test_notification_dashboard_view(self):
        """Тест дашборда уведомлений"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('notifications:dashboard'))
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('total_notifications', response.context)
        self.assertIn('unread_count', response.context)
    
    def test_notification_settings_view(self):
        """Тест настроек уведомлений"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('notifications:settings'))
        
        self.assertEqual(response.status_code, 200)
    
    def test_mark_notification_read(self):
        """Тест отметки уведомления как прочитанного"""
        self.client.login(username='testuser', password='testpass123')
        
        self.assertEqual(self.notification.status, 'unread')
        
        response = self.client.post(
            reverse('notifications:mark_read', kwargs={'notification_id': self.notification.pk})
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Обновляем объект из базы данных
        self.notification.refresh_from_db()
        self.assertEqual(self.notification.status, 'read')
    
    def test_mark_all_notifications_read(self):
        """Тест отметки всех уведомлений как прочитанных"""
        # Создаем еще одно непрочитанное уведомление
        Notification.objects.create(
            recipient=self.user,
            title='Второе уведомление',
            message='Тест',
            notification_type=self.notification_type
        )
        
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.post(reverse('notifications:mark_all_read'))
        
        self.assertEqual(response.status_code, 200)
        
        # Проверяем, что все уведомления отмечены как прочитанные
        unread_count = Notification.objects.filter(
            recipient=self.user,
            status='unread'
        ).count()
        
        self.assertEqual(unread_count, 0)


class NotificationAPITest(APITestCase):
    """Тесты для API уведомлений"""
    
    def setUp(self):
        """Настройка тестовых данных"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.notification_type = NotificationType.objects.create(
            name='Тестовое уведомление',
            code='test_notification'
        )
        
        self.notification = Notification.objects.create(
            recipient=self.user,
            title='Тестовое уведомление',
            message='Это тестовое сообщение',
            notification_type=self.notification_type
        )
        
        self.client.force_authenticate(user=self.user)
    
    def test_notification_list_api(self):
        """Тест API списка уведомлений"""
        url = reverse('notification-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['title'], 'Тестовое уведомление')
    
    def test_notification_detail_api(self):
        """Тест API детального представления уведомления"""
        url = reverse('notification-detail', kwargs={'pk': self.notification.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Тестовое уведомление')
    
    def test_notification_create_api(self):
        """Тест API создания уведомления"""
        url = reverse('notification-list')
        data = {
            'title': 'Новое уведомление',
            'message': 'Текст нового уведомления',
            'notification_type_id': self.notification_type.id,
            'recipient_id': self.user.id,
            'priority': 'medium'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Notification.objects.count(), 2)
    
    def test_notification_update_api(self):
        """Тест API обновления уведомления"""
        url = reverse('notification-detail', kwargs={'pk': self.notification.pk})
        data = {
            'status': 'read'
        }
        
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Обновляем объект из базы данных
        self.notification.refresh_from_db()
        self.assertEqual(self.notification.status, 'read')
    
    def test_unread_notifications_api(self):
        """Тест API непрочитанных уведомлений"""
        url = reverse('notification-unread')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
    
    def test_mark_as_read_api(self):
        """Тест API отметки как прочитанного"""
        url = reverse('notification-mark-as-read')
        data = {
            'notification_ids': [str(self.notification.pk)]
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Обновляем объект из базы данных
        self.notification.refresh_from_db()
        self.assertEqual(self.notification.status, 'read')
    
    def test_notification_stats_api(self):
        """Тест API статистики уведомлений"""
        url = reverse('notification-stats')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_notifications', response.data)
        self.assertIn('unread_count', response.data)
    
    def test_bulk_create_api(self):
        """Тест API массового создания уведомлений"""
        url = reverse('notification-bulk-create')
        data = {
            'title': 'Массовое уведомление',
            'message': 'Текст массового уведомления',
            'notification_type_id': self.notification_type.id,
            'recipient_ids': [self.user.id],
            'priority': 'high'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('created_count', response.data)


class NotificationServiceTest(TestCase):
    """Тесты для сервиса уведомлений"""
    
    def setUp(self):
        """Настройка тестовых данных"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.notification_type = NotificationType.objects.create(
            name='Тестовое уведомление',
            code='test_notification'
        )
        
        self.service = NotificationService()
    
    def test_send_notification(self):
        """Тест отправки уведомления"""
        notification = self.service.send_notification(
            recipient=self.user,
            title='Тестовое уведомление',
            message='Это тестовое сообщение',
            notification_type=self.notification_type,
            priority='high'
        )
        
        self.assertIsNotNone(notification)
        self.assertEqual(notification.recipient, self.user)
        self.assertEqual(notification.title, 'Тестовое уведомление')
        self.assertEqual(notification.priority, 'high')
    
    def test_send_bulk_notifications(self):
        """Тест массовой отправки уведомлений"""
        count = self.service.send_bulk_notifications(
            title='Массовое уведомление',
            message='Текст массового уведомления',
            recipient_ids=[self.user.id],
            notification_type=self.notification_type
        )
        
        self.assertEqual(count, 1)
        self.assertEqual(Notification.objects.count(), 1)
    
    def test_send_template_notification(self):
        """Тест отправки уведомления по шаблону"""
        template = NotificationTemplate.objects.create(
            name='Тестовый шаблон',
            notification_type=self.notification_type,
            title_template='Привет, {name}!',
            message_template='У вас {count} новых сообщений.'
        )
        
        notification = self.service.send_template_notification(
            template_name='Тестовый шаблон',
            recipient=self.user,
            context={'name': 'Пользователь', 'count': 5}
        )
        
        self.assertIsNotNone(notification)
        self.assertEqual(notification.title, 'Привет, Пользователь!')
        self.assertEqual(notification.message, 'У вас 5 новых сообщений.')
    
    def test_send_group_notification(self):
        """Тест отправки уведомления группе"""
        group = NotificationGroup.objects.create(
            name='Тестовая группа',
            notification_type=self.notification_type
        )
        group.recipients.add(self.user)
        
        count = self.service.send_group_notification(
            group_name='Тестовая группа',
            title='Групповое уведомление',
            message='Текст группового уведомления'
        )
        
        self.assertEqual(count, 1)
        self.assertEqual(Notification.objects.count(), 1)
    
    def test_cleanup_expired_notifications(self):
        """Тест очистки истекших уведомлений"""
        # Создаем истекшее уведомление
        expired_date = timezone.now() - timedelta(days=1)
        Notification.objects.create(
            recipient=self.user,
            title='Истекшее уведомление',
            message='Тест',
            notification_type=self.notification_type,
            expires_at=expired_date
        )
        
        # Создаем активное уведомление
        Notification.objects.create(
            recipient=self.user,
            title='Активное уведомление',
            message='Тест',
            notification_type=self.notification_type
        )
        
        # Очищаем истекшие уведомления
        cleaned_count = self.service.cleanup_expired_notifications()
        
        self.assertEqual(cleaned_count, 1)
        
        # Проверяем, что истекшее уведомление архивировано
        expired_notification = Notification.objects.get(title='Истекшее уведомление')
        self.assertEqual(expired_notification.status, 'archived')
        
        # Проверяем, что активное уведомление не затронуто
        active_notification = Notification.objects.get(title='Активное уведомление')
        self.assertEqual(active_notification.status, 'unread')
    
    def test_get_notification_stats(self):
        """Тест получения статистики уведомлений"""
        # Создаем несколько уведомлений
        Notification.objects.create(
            recipient=self.user,
            title='Уведомление 1',
            message='Тест',
            notification_type=self.notification_type,
            priority='high'
        )
        
        Notification.objects.create(
            recipient=self.user,
            title='Уведомление 2',
            message='Тест',
            notification_type=self.notification_type,
            priority='medium'
        )
        
        stats = self.service.get_notification_stats(self.user)
        
        self.assertEqual(stats['total'], 2)
        self.assertEqual(stats['unread'], 2)
        self.assertIn('high', stats['by_priority'])
        self.assertIn('medium', stats['by_priority'])


class NotificationIntegrationTest(TestCase):
    """Интеграционные тесты для уведомлений"""
    
    def setUp(self):
        """Настройка тестовых данных"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.notification_type = NotificationType.objects.create(
            name='Тестовое уведомление',
            code='test_notification'
        )
        
        # Создаем настройки уведомлений
        NotificationPreference.objects.create(
            user=self.user,
            email_notifications=True,
            push_notifications=True,
            sms_notifications=False
        )
    
    def test_full_notification_flow(self):
        """Тест полного цикла работы с уведомлениями"""
        # 1. Создаем уведомление через сервис
        service = NotificationService()
        notification = service.send_notification(
            recipient=self.user,
            title='Интеграционный тест',
            message='Проверка полного цикла',
            notification_type=self.notification_type,
            priority='high'
        )
        
        self.assertIsNotNone(notification)
        
        # 2. Проверяем через API
        self.client.login(username='testuser', password='testpass123')
        
        # Список уведомлений
        response = self.client.get(reverse('notifications:list'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(notification, response.context['notifications'])
        
        # Детальное представление
        response = self.client.get(
            reverse('notifications:detail', kwargs={'pk': notification.pk})
        )
        self.assertEqual(response.status_code, 200)
        
        # 3. Отмечаем как прочитанное
        response = self.client.post(
            reverse('notifications:mark_read', kwargs={'notification_id': notification.pk})
        )
        self.assertEqual(response.status_code, 200)
        
        # 4. Проверяем статус
        notification.refresh_from_db()
        self.assertEqual(notification.status, 'read')
        
        # 5. Проверяем статистику
        response = self.client.get(reverse('notifications:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['unread_count'], 0)
    
    def test_notification_filters(self):
        """Тест фильтрации уведомлений"""
        # Создаем уведомления с разными параметрами
        service = NotificationService()
        
        service.send_notification(
            recipient=self.user,
            title='Высокий приоритет',
            message='Тест',
            notification_type=self.notification_type,
            priority='high'
        )
        
        service.send_notification(
            recipient=self.user,
            title='Низкий приоритет',
            message='Тест',
            notification_type=self.notification_type,
            priority='low'
        )
        
        self.client.login(username='testuser', password='testpass123')
        
        # Фильтр по приоритету
        response = self.client.get(
            reverse('notifications:filters'),
            {'priority': 'high'}
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data['notifications']), 1)
        self.assertEqual(data['notifications'][0]['priority'], 'high')
    
    def test_notification_export(self):
        """Тест экспорта уведомлений"""
        # Создаем несколько уведомлений
        service = NotificationService()
        for i in range(3):
            service.send_notification(
                recipient=self.user,
                title=f'Уведомление {i+1}',
                message=f'Текст {i+1}',
                notification_type=self.notification_type
            )
        
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('notifications:export'))
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        
        # Проверяем содержимое CSV
        content = response.content.decode('utf-8')
        lines = content.strip().split('\n')
        
        # Заголовок + 3 уведомления
        self.assertEqual(len(lines), 4)
        self.assertIn('ID,Заголовок,Сообщение,Тип,Приоритет,Статус,Дата создания,Дата прочтения', lines[0]) 