from django.urls import path, include
from .views import FinishedGoodsPageView
from rest_framework.routers import DefaultRouter
from .views import FinishedGoodViewSet

router = DefaultRouter()
router.register(r'finished_goods', FinishedGoodViewSet, basename='finishedgood')

urlpatterns = [
    path('api/', include(router.urls)),
    path('', FinishedGoodsPageView.as_view(), name='finished_goods_page'),
] 