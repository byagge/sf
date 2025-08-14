from django.shortcuts import render
from rest_framework import viewsets, permissions
from .models import FinishedGood
from .serializers import FinishedGoodSerializer, FinishedGoodDetailSerializer
from django.views.generic import TemplateView
from rest_framework.response import Response
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache

# Create your views here.

class FinishedGoodViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = FinishedGood.objects.select_related('product', 'order').all().order_by('-received_at')
    serializer_class = FinishedGoodSerializer
    permission_classes = [permissions.IsAuthenticated]

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = FinishedGoodDetailSerializer(instance, context={'request': request})
        return Response(serializer.data)

class FinishedGoodsPageView(TemplateView):
    template_name = 'finished_goods.html'

    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        is_mobile = any(m in user_agent for m in ['iphone', 'android', 'ipad', 'mobile', 'opera mini', 'blackberry'])
        if is_mobile:
            self.template_name = 'finished_mobile.html'
        else:
            self.template_name = 'finished_goods.html'
        return super().dispatch(request, *args, **kwargs)
