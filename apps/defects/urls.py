from rest_framework.routers import DefaultRouter
from .views import DefectViewSet, DefectRepairTaskViewSet, DefectPageView
from django.urls import path, include

router = DefaultRouter()
router.register(r'defects', DefectViewSet, basename='defect')
router.register(r'repair-tasks', DefectRepairTaskViewSet, basename='defect-repair-task')

urlpatterns = [
    path('api/', include(router.urls)),
    path('', DefectPageView.as_view(), name='defects-page'),
] 