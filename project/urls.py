from django.urls import path, include
from django.views.generic import TemplateView

urlpatterns = [
    # ... другие url ...
    path('', include('apps.users.urls')),  # Включаем users URLs в корень
    path('employee_tasks/', include('apps.employee_tasks.urls')),
    path('workshops/', include('apps.workshops.urls')),
    path('orders/', include('apps.orders.urls')),
    path('services/', include('apps.services.urls')),
    path('notifications/', include('apps.notifications.urls', namespace='notifications')),
    path('plans/master/', TemplateView.as_view(template_name='plans_master.html')),
] 