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
from django.conf import settings
from django.conf.urls.static import static
from .views import (
    home, handler404, handler500, handler400, 
    handler401, handler403, handler_error, api_test
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    path('api/test/', api_test, name='api_test'),
    
    # Apps URLs
    path('employees/', include('apps.employees.urls')),
    path('clients/', include('apps.clients.urls')),
    path('defects/', include('apps.defects.urls')),
    path('director/', include('apps.director.urls')),
    path('employee-tasks/', include('apps.employee_tasks.urls')),
    path('executive/', include('apps.executive.dashboard.urls')),
    path('finance/', include('apps.finance.urls')),
    path('finished-goods/', include('apps.finished_goods.urls')),
    path('inventory/', include('apps.inventory.urls')),
    path('notifications/', include('apps.notifications.urls')),
    path('odashboard/', include('apps.odashboard.urls')),
    path('operations/', include('apps.operations.workshops.urls')),
    path('orders/', include('apps.orders.urls')),
    path('plans/', include('apps.plans.urls')),
    path('products/', include('apps.products.urls')),
    path('services/', include('apps.services.urls')),
    path('users/', include('apps.users.urls')),
    path('workshops/', include('apps.workshops.urls')),
    path('attendance/', include('apps.attendance.urls')),
]

# Error handlers
handler404 = 'core.views.handler404'
handler500 = 'core.views.handler500'
handler400 = 'core.views.handler400'
handler401 = 'core.views.handler401'
handler403 = 'core.views.handler403'

# Custom error URLs for testing
if settings.DEBUG:
    urlpatterns += [
        path('error/400/', handler400, name='error_400'),
        path('error/401/', handler401, name='error_401'),
        path('error/403/', handler403, name='error_403'),
        path('error/404/', handler404, name='error_404'),
        path('error/500/', handler500, name='error_500'),
        path('error/custom/', handler_error, name='error_custom'),
    ]

# Static and media files
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

