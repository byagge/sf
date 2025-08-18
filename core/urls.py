"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app import views
    2. Add a URL to urlpatterns:  path('', other_app.views.Home, name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView, RedirectView
from .views import HomeView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', HomeView.as_view(), name='home'),  # Корневой URL с проверкой ролей
    path('accounts/', include('users.urls')),
    path('settings/', RedirectView.as_view(url='/accounts/profile/', permanent=False), name='settings'),  # Редирект на профиль
    path('clients/', include('clients.urls')),  # Изменяем с '' на 'clients/'
    path('workshops/', include('apps.operations.workshops.urls')),
    path('dashboard/', include('apps.odashboard.urls')),
    path('employees/', include('apps.employees.urls')),
    path('inventory/', include('apps.inventory.urls')),
    path('services/', include('apps.services.urls')),
    path('products/', include('apps.products.urls')),
    path('defects/', include('apps.defects.urls')),
    path('orders/', include('apps.orders.urls')),
    path('finished_goods/', include('apps.finished_goods.urls')),
    path('attendance/', include('apps.attendance.urls')),
    path('employee_tasks/', include('apps.employee_tasks.urls')),
    path('finance/', include('apps.finance.urls')),
    path('api/workshops/', include('apps.workshops.urls')),  # Прямой маршрут для API
    path('admin/', admin.site.urls),
    path('stats/', TemplateView.as_view(template_name='stats_master.html'), name='stats-master'),
    path('notifications/', TemplateView.as_view(template_name='coming_soon.html'), name='coming_soon'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

