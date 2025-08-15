from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'defects', views.DefectViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/stats/', views.DefectStatsAPIView.as_view(), name='defect-stats'),
    path('', views.DefectPageView.as_view(), name='defects'),
] 