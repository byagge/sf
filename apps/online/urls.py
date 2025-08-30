from django.urls import path
from . import views

app_name = 'online'

urlpatterns = [
    path('', views.online_users_view, name='online_users'),
    path('api/', views.online_users_api, name='online_users_api'),
    path('user/<int:user_id>/', views.user_activity_detail, name='user_activity_detail'),
] 