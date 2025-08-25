from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views, api

router = DefaultRouter()
router.register(r'employee-tasks', api.EmployeeTaskViewSet)
router.register(r'helper-tasks', api.HelperTaskViewSet)

urlpatterns = [
    path('tasks/', views.task_list, name='task_list'),
    path('tasks/<int:task_id>/', views.task_detail, name='task_detail'),
    path('stats/', views.stats_view, name='stats_view'),
    path('api/', include(router.urls)),
    path('assign/', views.assign_task, name='assign_task'),
    path('assign/<int:assignment_id>/', views.edit_assignment, name='edit_assignment'),
] 