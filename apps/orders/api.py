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
        
        print(f"=== API DEBUG: workshop_id={workshop_id}, status={status} ===")
        
        # Получаем этапы с базовой информацией
        stages = OrderStage.objects.select_related(
            'order_item__product',
            'order_item__order',
            'order_item__order__client',
            'workshop'
        ).prefetch_related(
            'order_item__order__items__product'
        ).filter(workshop_id=workshop_id, status=status)
        
        print(f"=== API DEBUG: Found {stages.count()} stages ===")
        
        # Обрабатываем каждый этап и добавляем данные заказа
        stages_data = []
        for stage in stages:
            print(f"=== API DEBUG: Processing stage {stage.id} ===")
            print(f"  - order: {stage.order}")
            print(f"  - order_item: {stage.order_item}")
            
            stage_data = OrderStageSerializer(stage).data
            
            # Всегда добавляем данные заказа, если они есть
            if stage.order:
                try:
                    # Получаем все товары заказа
                    order_items = stage.order.items.all()
                    print(f"  - order_items count: {order_items.count()}")
                    
                    # Если у этапа нет order_item, создаем виртуальный
                    if not stage.order_item:
                        print(f"  - Creating virtual order_item")
                        if order_items.exists():
                            stage_data['order_item'] = {
                                'id': None,
                                'product': None,
                                'order': OrderSerializer(stage.order).data,
                                'items': OrderItemSerializer(order_items, many=True).data
                            }
                            print(f"  - Virtual order_item created with {len(stage_data['order_item']['items'])} items")
                    else:
                        print(f"  - Adding order data to existing order_item")
                        # Если у этапа есть order_item, добавляем данные заказа к нему
                        if not stage_data.get('order_item', {}).get('order'):
                            stage_data['order_item']['order'] = OrderSerializer(stage.order).data
                        if not stage_data.get('order_item', {}).get('items'):
                            stage_data['order_item']['items'] = OrderItemSerializer(order_items, many=True).data
                        print(f"  - Order data added to order_item")
                            
                except Exception as e:
                    print(f"Error getting order data for stage {stage.id}: {e}")
            else:
                print(f"  - No order found for stage")
            
            stages_data.append(stage_data)
        
        print(f"=== API DEBUG: Returning {len(stages_data)} stages ===")
        for i, stage_data in enumerate(stages_data):
            print(f"  Stage {i+1}: order_item={stage_data.get('order_item') is not None}")
            if stage_data.get('order_item'):
                print(f"    - order: {stage_data['order_item'].get('order') is not None}")
                print(f"    - items: {stage_data['order_item'].get('items') is not None}")
        
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