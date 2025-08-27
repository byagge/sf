from django.urls import path
from . import views

urlpatterns = [
    path('', views.service_list, name='service_list'),
    path('create/', views.service_create, name='service_create'),
    path('<int:pk>/edit/', views.service_edit, name='service_edit'),
    path('<int:pk>/delete/', views.service_delete, name='service_delete'),
    path('<int:pk>/duplicate/', views.service_duplicate, name='service_duplicate'),
    path('api/services/', views.api_service_list, name='api_service_list'),
    path('api/services/create/', views.api_service_create, name='api_service_create'),
    path('api/services/<int:pk>/update/', views.api_service_update, name='api_service_update'),
    path('api/services/<int:pk>/delete/', views.api_service_delete, name='api_service_delete'),
    path('api/services/bulk-delete/', views.api_service_bulk_delete, name='api_service_bulk_delete'),
    path('api/services/stats/', views.api_service_stats, name='api_service_stats'),
    path('api/services/<int:pk>/duplicate/', views.api_service_duplicate, name='api_service_duplicate'),
    path('api/materials/', views.api_materials, name='api_materials'),
    path('api/workshops/', views.api_workshops, name='api_workshops'),
    
    # API для мастера
    path('master/', views.master_services, name='master_services'),
    path('api/master/services/', views.api_master_services, name='api_master_services'),
    path('api/master/services/<int:pk>/update-price/', views.api_master_update_price, name='api_master_update_price'),
    path('api/master/workshops/', views.api_master_workshops, name='api_master_workshops'),
] 