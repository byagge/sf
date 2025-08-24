from django.urls import path
from . import views
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'api/workshops', views.WorkshopViewSet, basename='workshop')

urlpatterns = [
    path('', views.workshops_list, name='workshops'),
    path('mobile/', views.workshops_mobile_page, name='workshops-mobile'),
    path('master/', views.master_dashboard, name='master-dashboard'),
    path('api/workshops/<int:workshop_id>/orders/', views.workshop_orders_info, name='workshop-orders-info'),
    path('api/workshops/orders/', views.all_workshops_orders_info, name='all-workshops-orders-info'),
]

urlpatterns += router.urls 