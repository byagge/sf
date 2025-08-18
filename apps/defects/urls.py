from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'defects', views.DefectViewSet)

urlpatterns = [
    # Страницы
    path('', views.defects_page, name='defects_page'),
    path('mobile/', views.defects_mobile_page, name='defects_mobile_page'),
    
    # API
    path('api/', include(router.urls)),
    path('api/defects/', views.defects_list, name='defects_list'),
    path('api/defects/<int:defect_id>/confirm/', views.confirm_defect, name='confirm_defect'),
    path('api/defects/<int:defect_id>/mark_repaired/', views.mark_defect_repaired, name='mark_defect_repaired'),
    path('api/defects/<int:defect_id>/close/', views.close_defect, name='close_defect'),
    path('api/stats/', views.defects_stats, name='defects_stats'),
] 