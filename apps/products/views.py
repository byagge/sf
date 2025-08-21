from django.views import View
from django.shortcuts import render
from rest_framework import viewsets
from .models import Product
from .serializers import ProductSerializer

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().prefetch_related('services').order_by('name', 'id')
    serializer_class = ProductSerializer

class ProductsPageView(View):
    def get(self, request):
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        is_mobile = any(m in user_agent for m in ['iphone', 'android', 'ipad', 'mobile'])
        template = 'products_mobile.html' if is_mobile else 'products.html'
        return render(request, template)
