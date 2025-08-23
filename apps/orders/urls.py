from rest_framework.routers import DefaultRouter
from .views import OrderViewSet, OrderPageView, OrderCreateAPIView, OrderStageConfirmAPIView, StageViewSet, OrderStageTransferAPIView, OrderStagePostponeAPIView, OrderStageNoTransferAPIView, DashboardOverviewAPIView, DashboardRevenueChartAPIView, PlansMasterView, PlansMasterDetailView
from .api import WorkshopStagesView, StageDetailView
from django.urls import path, include
from django.views.generic import TemplateView

router = DefaultRouter()
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'stages', StageViewSet, basename='stage')

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/create/', OrderCreateAPIView.as_view(), name='order-create-api'),
    path('api/stages/<int:stage_id>/transfer/', OrderStageTransferAPIView.as_view(), name='order-stage-transfer'),
    path('api/stages/<int:stage_id>/postpone/', OrderStagePostponeAPIView.as_view(), name='order-stage-postpone'),
    path('api/stages/<int:stage_id>/no-transfer/', OrderStageNoTransferAPIView.as_view(), name='order-stage-no-transfer'),
    path('api/stages/<int:stage_id>/confirm/', OrderStageConfirmAPIView.as_view(), name='order-stage-confirm'),
    path('api/stages/<int:stage_id>/', StageDetailView.as_view(), name='stage-detail'),
    path('api/stages/', WorkshopStagesView.as_view()),
    path('', OrderPageView.as_view(), name='orders-page'),
    path('plans/master/', PlansMasterView.as_view(), name='plans-master'),
    path('plans/master/<int:stage_id>/', PlansMasterDetailView.as_view(), name='plans-master-detail'),
    path('dashboard/overview/', DashboardOverviewAPIView.as_view(), name='dashboard-overview'),
    path('dashboard/revenue-chart/', DashboardRevenueChartAPIView.as_view(), name='dashboard-revenue-chart'),
] 