from django.urls import path
from . import views

urlpatterns = [
	path('', views.dashboard, name='director_dashboard'),
	path('mobile/', views.dashboard_mobile, name='director_dashboard_mobile'),
] 