from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import Order, OrderItem, OrderStage
from .serializers import OrderSerializer, OrderItemSerializer, OrderStageSerializer
from apps.operations.workshops.models import Workshop

class WorkshopStagesView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        workshop_id = request.GET.get('workshop')
        status_filter = request.GET.get('status', 'in_progress')
        
        print(f"DEBUG WorkshopStagesView: workshop_id={workshop_id}, status_filter={status_filter}")
        
        if not workshop_id:
            return Response({'error': 'Workshop ID required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            workshop = Workshop.objects.get(id=workshop_id)
            print(f"DEBUG: Найден цех: {workshop.name}")
        except Workshop.DoesNotExist:
            return Response({'error': 'Workshop not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Получаем этапы для указанного цеха
        stages = OrderStage.objects.filter(workshop=workshop, status=status_filter)
        print(f"DEBUG: Найдено этапов для цеха {workshop.name}: {stages.count()}")
        
        # Сериализуем данные
        stage_data = []
        for stage in stages:
            print(f"DEBUG: Обрабатываем этап {stage.id}: {stage.operation}")
            stage_info = {
                'id': stage.id,
                'order_name': stage.order.name if stage.order else 'Без названия',
                'operation': stage.operation,
                'plan_quantity': stage.plan_quantity,
                'completed_quantity': stage.completed_quantity,
                'done_count': stage.done_count,
                'created_at': stage.created_at,
                'workshop_name': workshop.name,
                'workshop_info': {
                    'workshop_name': workshop.name,
                    'cutting_specs': stage.cutting_specs,
                    'cnc_specs': stage.cnc_specs,
                    'paint_type': stage.paint_type,
                    'paint_color': stage.paint_color,
                },
                'assigned': []
            }
            
            # Получаем назначения для этапа
            if hasattr(stage, 'employee_tasks'):
                for task in stage.employee_tasks.all():
                    stage_info['assigned'].append({
                        'id': task.id,
                        'employee_id': task.employee.id,
                        'employee_name': f"{task.employee.first_name} {task.employee.last_name}".strip() or task.employee.username,
                        'quantity': task.quantity,
                        'completed_quantity': task.completed_quantity,
                        'defective_quantity': task.defective_quantity
                    })
            
            # Получаем информацию о товаре заказа
            if hasattr(stage, 'order_item') and stage.order_item:
                stage_info['order_item'] = {
                    'id': stage.order_item.id,
                    'product': {
                        'name': stage.order_item.product.name if stage.order_item.product else 'Товар',
                        'is_glass': stage.order_item.product.is_glass if stage.order_item.product else False,
                        'glass_type': stage.order_item.product.glass_type if stage.order_item.product else None,
                    },
                    'size': stage.order_item.size,
                    'color': stage.order_item.color,
                    'paint_type': stage.order_item.paint_type,
                    'paint_color': stage.order_item.paint_color,
                    'cnc_specs': stage.order_item.cnc_specs,
                    'cutting_specs': stage.order_item.cutting_specs,
                    'packaging_notes': stage.order_item.packaging_notes,
                    'glass_type_display': stage.order_item.glass_type_display if hasattr(stage.order_item, 'glass_type_display') else None,
                    'order': {
                        'id': stage.order_item.order.id,
                        'name': stage.order_item.order.name,
                        'status': stage.order_item.order.status,
                        'status_display': stage.order_item.order.get_status_display(),
                        'created_at': stage.order_item.order.created_at,
                        'comment': stage.order_item.order.comment,
                        'client': {
                            'name': stage.order_item.order.client.name if stage.order_item.order.client else None,
                        } if stage.order_item.order.client else None,
                        'items': []
                    } if stage.order_item.order else None
                }
                
                # Получаем все товары заказа
                if stage.order_item.order:
                    for item in stage.order_item.order.items.all():
                        stage_info['order_item']['order']['items'].append({
                            'id': item.id,
                            'product': {
                                'name': item.product.name if item.product else 'Товар'
                            },
                            'quantity': item.quantity,
                            'size': item.size,
                            'color': item.color
                        })
            
            stage_data.append(stage_info)
        
        print(f"DEBUG: Возвращаем {len(stage_data)} этапов")
        return Response(stage_data)

class StageDetailView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, stage_id):
        stage = get_object_or_404(OrderStage, id=stage_id)
        serializer = OrderStageSerializer(stage)
        return Response(serializer.data)

# Новые API views для заявок
class NewRequestsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Получение новых заявок, которые еще не распределены по цехам"""
        try:
            # Получаем все заявки со статусом "new" или "pending"
            all_orders = Order.objects.all()
            print(f"DEBUG: Всего заявок в базе: {all_orders.count()}")
            
            for order in all_orders:
                print(f"DEBUG: Заявка {order.id}: статус='{order.status}', этапов={order.stages.count()}")
            
            # Получаем заявки со статусом "new" или "pending"
            new_orders = Order.objects.filter(
                status__in=['new', 'pending']
            )
            print(f"DEBUG: Заявки со статусом new/pending: {new_orders.count()}")
            
            # Получаем заявки без этапов
            orders_without_stages = Order.objects.filter(
                stages__isnull=True
            )
            print(f"DEBUG: Заявки без этапов: {orders_without_stages.count()}")
            
            # Объединяем условия: заявки со статусом new/pending И без этапов
            final_orders = Order.objects.filter(
                status__in=['new', 'pending']
            ).filter(
                stages__isnull=True  # Заявки БЕЗ этапов
            ).distinct()
            
            print(f"DEBUG: Итоговые заявки для отображения: {final_orders.count()}")
            
            requests_data = []
            for order in final_orders:
                print(f"DEBUG: Обрабатываем заявку {order.id}: {order.name}")
                request_info = {
                    'id': order.id,
                    'name': order.name,
                    'created_at': order.created_at,
                    'client': {
                        'name': order.client.name if order.client else None,
                    } if order.client else None,
                    'items': []
                }
                
                # Получаем товары заявки
                for item in order.items.all():
                    print(f"DEBUG: Товар заявки {order.id}: {item.product.name if item.product else 'Без названия'}")
                    request_info['items'].append({
                        'id': item.id,
                        'product': {
                            'name': item.product.name if item.product else 'Товар'
                        },
                        'quantity': item.quantity,
                        'size': item.size,
                        'color': item.color
                    })
                
                requests_data.append(request_info)
            
            print(f"DEBUG: Возвращаем {len(requests_data)} заявок")
            return Response(requests_data)
            
        except Exception as e:
            print(f"ERROR в NewRequestsView: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AssignRequestToWorkshopView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pk):
        """Назначение заявки в конкретный цех"""
        try:
            order = Order.objects.get(id=pk)
            workshop_id = request.data.get('workshop_id')
            
            if not workshop_id:
                return Response({'error': 'Workshop ID required'}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                workshop = Workshop.objects.get(id=workshop_id)
            except Workshop.DoesNotExist:
                return Response({'error': 'Workshop not found'}, status=status.HTTP_404_NOT_FOUND)
            
            # Создаем этап для каждого товара в заявке
            for item in order.items.all():
                # Определяем операцию на основе типа товара и цеха
                operation = f"Обработка {item.product.name if item.product else 'товара'}"
                
                # Если это стеклянное изделие и цех распила/обработки
                if item.product and item.product.is_glass:
                    if 'распил' in workshop.name.lower() or 'резка' in workshop.name.lower():
                        operation = "Распил стекла"
                    elif 'обработка' in workshop.name.lower() or 'чпу' in workshop.name.lower():
                        operation = "Обработка стекла"
                
                OrderStage.objects.create(
                    order=order,
                    order_item=item,
                    workshop=workshop,
                    operation=operation,
                    plan_quantity=item.quantity,
                    status='in_progress',
                    # Копируем спецификации из товара заказа
                    cutting_specs=item.cutting_specs,
                    cnc_specs=item.cnc_specs,
                    paint_type=item.paint_type,
                    paint_color=item.paint_color,
                )
            
            # Обновляем статус заявки
            order.status = 'in_progress'
            order.save()
            
            return Response({'message': 'Request assigned to workshop successfully'}, status=status.HTTP_200_OK)
            
        except Order.DoesNotExist:
            return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 