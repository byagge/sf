from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from .models import UserActivity

User = get_user_model()

class OnlineAppTestCase(TestCase):
    def setUp(self):
        # Создаем тестовых пользователей
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            is_staff=True,
            is_superuser=True
        )
        
        self.staff_user = User.objects.create_user(
            username='staff',
            email='staff@test.com',
            password='testpass123',
            is_staff=True
        )
        
        self.regular_user = User.objects.create_user(
            username='user',
            email='user@test.com',
            password='testpass123',
            is_staff=False
        )
        
        self.client = Client()
        
        # Создаем записи активности
        self.admin_activity = UserActivity.objects.create(
            user=self.admin_user,
            last_seen=timezone.now(),
            is_online=True
        )
        
        self.staff_activity = UserActivity.objects.create(
            user=self.staff_user,
            last_seen=timezone.now(),
            is_online=True
        )

    def test_online_users_view_staff_access(self):
        """Тест доступа к странице онлайн пользователей для staff"""
        # Вход как staff пользователь
        self.client.login(username='staff', password='testpass123')
        
        response = self.client.get(reverse('online:online_users'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Онлайн пользователи')
        self.assertContains(response, 'admin')
        self.assertContains(response, 'staff')

    def test_online_users_view_regular_user_access_denied(self):
        """Тест отказа в доступе для обычного пользователя"""
        # Вход как обычный пользователь
        self.client.login(username='user', password='testpass123')
        
        response = self.client.get(reverse('online:online_users'))
        self.assertEqual(response.status_code, 302)  # Редирект

    def test_online_users_view_unauthenticated_access_denied(self):
        """Тест отказа в доступе для неаутентифицированного пользователя"""
        response = self.client.get(reverse('online:online_users'))
        self.assertEqual(response.status_code, 302)  # Редирект на страницу входа

    def test_online_users_api_staff_access(self):
        """Тест доступа к API для staff"""
        self.client.login(username='staff', password='testpass123')
        
        response = self.client.get(reverse('online:online_users_api'))
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('users', data)
        self.assertIn('total', data)
        self.assertEqual(data['total'], 2)

    def test_online_users_api_regular_user_access_denied(self):
        """Тест отказа в доступе к API для обычного пользователя"""
        self.client.login(username='user', password='testpass123')
        
        response = self.client.get(reverse('online:online_users_api'))
        self.assertEqual(response.status_code, 403)

    def test_user_activity_detail_staff_access(self):
        """Тест доступа к деталям активности для staff"""
        self.client.login(username='staff', password='testpass123')
        
        response = self.client.get(
            reverse('online:user_activity_detail', args=[self.admin_user.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'admin')

    def test_user_activity_detail_regular_user_access_denied(self):
        """Тест отказа в доступе к деталям для обычного пользователя"""
        self.client.login(username='user', password='testpass123')
        
        response = self.client.get(
            reverse('online:user_activity_detail', args=[self.admin_user.id])
        )
        self.assertEqual(response.status_code, 302)

    def test_user_activity_model(self):
        """Тест модели UserActivity"""
        # Тест создания записи
        activity = UserActivity.objects.create(
            user=self.regular_user,
            last_seen=timezone.now(),
            is_online=True
        )
        
        self.assertEqual(activity.user, self.regular_user)
        self.assertTrue(activity.is_online)
        
        # Тест строкового представления
        self.assertIn(self.regular_user.username, str(activity))
        
        # Тест метода get_online_users
        online_users = UserActivity.get_online_users()
        self.assertEqual(online_users.count(), 3)
        
        # Тест метода update_user_activity
        old_time = activity.last_seen
        UserActivity.update_user_activity(self.regular_user)
        activity.refresh_from_db()
        self.assertGreater(activity.last_seen, old_time)

    def test_middleware_updates_activity(self):
        """Тест middleware для обновления активности"""
        # Создаем клиент с middleware
        from django.test import RequestFactory
        from apps.online.middleware import UserActivityMiddleware
        
        factory = RequestFactory()
        request = factory.get('/')
        request.user = self.regular_user
        
        middleware = UserActivityMiddleware(lambda req: None)
        middleware(request)
        
        # Проверяем, что активность обновлена
        activity = UserActivity.objects.get(user=self.regular_user)
        self.assertTrue(activity.is_online)
        self.assertGreaterEqual(activity.last_seen, timezone.now() - timezone.timedelta(minutes=1))
