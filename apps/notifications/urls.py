from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Настройка роутера для API
router = DefaultRouter()
router.register(r'api/notifications', views.NotificationViewSet, basename='notification')
router.register(r'api/notification-types', views.NotificationTypeViewSet, basename='notification-type')
router.register(r'api/notification-templates', views.NotificationTemplateViewSet, basename='notification-template')
router.register(r'api/notification-groups', views.NotificationGroupViewSet, basename='notification-group')
router.register(r'api/notification-preferences', views.NotificationPreferenceViewSet, basename='notification-preference')

app_name = 'notifications'

# URL-маршруты для Django представлений
urlpatterns = [
	# Основные страницы
	path('', views.NotificationListView.as_view(), name='list'),
	path('dashboard/', views.NotificationDashboardView.as_view(), name='dashboard'),
	path('settings/', views.NotificationSettingsView.as_view(), name='settings'),

	# Coming soon
	path('coming-soon/', views.NotificationsComingSoonView.as_view(), name='coming_soon'),
	
	# Детальные страницы
	path('notification/<uuid:pk>/', views.NotificationDetailView.as_view(), name='detail'),
	
	# Создание и редактирование
	path('create/', views.NotificationCreateView.as_view(), name='create'),
	
	# Административные страницы
	path('admin/', views.AdminNotificationListView.as_view(), name='admin_list'),
	path('admin/create/', views.AdminNotificationCreateView.as_view(), name='admin_create'),
	
	# Компоненты
	path('bell/', views.notification_bell, name='bell'),
	path('unread-count/', views.unread_count, name='unread_count'),
]

# Добавляем API маршруты
urlpatterns += router.urls 