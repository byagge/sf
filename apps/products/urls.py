from rest_framework.routers import DefaultRouter
from .views import ProductViewSet, ProductsPageView
from django.urls import path, include

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')

urlpatterns = [
    path('api/', include(router.urls)),
    path('', ProductsPageView.as_view(), name='products-page'),
] 