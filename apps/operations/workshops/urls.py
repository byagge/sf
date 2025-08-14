from django.urls import path
from . import views
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'api/workshops', views.WorkshopViewSet, basename='workshop')

urlpatterns = [
    path('', views.workshops_list, name='workshops'),
]

urlpatterns += router.urls 