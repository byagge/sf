from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import ClientViewSet
from django.views.generic import TemplateView
from . import views

router = DefaultRouter()
router.register(r'api/clients', ClientViewSet, basename='client')

urlpatterns = [
    path('', views.clients_page, name='clients-page'),
]

urlpatterns += router.urls 