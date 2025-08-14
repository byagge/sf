from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('workshop-dashboard/', views.workshop_dashboard, name='workshop_dashboard'),
] 