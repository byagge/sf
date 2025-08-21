from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('workshop-dashboard/', views.workshop_dashboard, name='workshop_dashboard'),
    path('workshop-dashboard/overview/', views.workshop_dashboard_overview, name='workshop_dashboard_overview'),
    path('workshop-dashboard/production-chart/', views.workshop_production_chart, name='workshop_production_chart'),
] 