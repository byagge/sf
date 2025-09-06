from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import OrderStage
from .serializers import OrderStageSerializer
from django.shortcuts import get_object_or_404
from django.db.models import Q

class WorkshopStagesView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        workshop_id = request.GET.get('workshop')
        status = request.GET.get('status')
        
        # Базовый запрос
        stages = OrderStage.objects.select_related(
            'order',
            'order__client',
            'order_item__product',
            'order_item__order',
            'order_item__order__client',
            'workshop'
        ).prefetch_related(
            'order__items__product',
            'order_item__order__items__product'
        ).filter(workshop_id=workshop_id, status=status)
        
        # Фильтрация стеклянных изделий для цехов после ID5
        workshop_id_int = int(workshop_id) if workshop_id else 0
        if workshop_id_int > 5:
            # Для цехов после ID5 исключаем стеклянные изделия
            stages = stages.exclude(
                Q(order_item__product__is_glass=True) | 
                Q(order_item__isnull=True, order__items__product__is_glass=True)
            ).distinct()
        
        return Response(OrderStageSerializer(stages, many=True).data) 

class StageDetailView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, stage_id):
        stage = get_object_or_404(
            OrderStage.objects.select_related(
                'order',
                'order__client',
                'order_item__product',
                'order_item__order',
                'order_item__order__client',
                'workshop'
            ).prefetch_related(
                'order__items__product',
                'order_item__order__items__product'
            ),
            id=stage_id
        )
        return Response(OrderStageSerializer(stage).data) 