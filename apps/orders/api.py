from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import OrderStage
from .serializers import OrderStageSerializer, OrderSerializer, OrderItemSerializer
from django.shortcuts import get_object_or_404

class WorkshopStagesView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        workshop_id = request.GET.get('workshop')
        status = request.GET.get('status')
        
        # Получаем этапы с базовой информацией
        stages = OrderStage.objects.select_related(
            'order_item__product',
            'order_item__order',
            'order_item__order__client',
            'workshop'
        ).prefetch_related(
            'order_item__order__items__product'
        ).filter(workshop_id=workshop_id, status=status)
        
        # Для этапов без order_item, получаем данные заказа отдельно
        stages_data = []
        for stage in stages:
            stage_data = OrderStageSerializer(stage).data
            
            # Если у этапа нет order_item, но есть order, получаем данные заказа
            if not stage.order_item and stage.order:
                try:
                    # Получаем все товары заказа
                    order_items = stage.order.items.all()
                    if order_items.exists():
                        # Создаем виртуальный order_item с данными заказа
                        stage_data['order_item'] = {
                            'id': None,
                            'product': None,
                            'order': OrderSerializer(stage.order).data,
                            'items': OrderItemSerializer(order_items, many=True).data
                        }
                except Exception as e:
                    print(f"Error getting order data for stage {stage.id}: {e}")
            
            stages_data.append(stage_data)
        
        return Response(stages_data) 

class StageDetailView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, stage_id):
        stage = get_object_or_404(
            OrderStage.objects.select_related(
                'order_item__product',
                'order_item__order',
                'order_item__order__client',
                'workshop'
            ).prefetch_related(
                'order_item__order__items__product'
            ),
            id=stage_id
        )
        return Response(OrderStageSerializer(stage).data) 