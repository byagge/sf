from django.urls import path
from . import views
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'api/workshops', views.WorkshopViewSet, basename='workshop')

urlpatterns = [
    path('', views.workshops_list, name='workshops'),
    path('mobile/', views.workshops_mobile_page, name='workshops-mobile'),
    path('master/', views.master_dashboard_page, name='workshop-master'),
    path('master/workshops/', views.master_workshops_page, name='master-workshops'),
    path('api/workshops/<int:workshop_id>/orders/', views.workshop_orders_info, name='workshop-orders-info'),
    path('api/workshops/orders/', views.all_workshops_orders_info, name='all-workshops-orders-info'),
    
    # Новые endpoints для мастера
    path('api/master/workshops/', views.master_workshops, name='master-workshops'),
    path('api/master/overview/', views.master_overview, name='master-overview'),
    path('api/master/workshop/<int:workshop_id>/stats/', views.workshop_detailed_stats, name='workshop-detailed-stats'),
]

urlpatterns += router.urls 