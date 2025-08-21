from rest_framework import serializers
from .models import EmployeeTask

class EmployeeTaskSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    done_quantity = serializers.SerializerMethodField()
    stage_name = serializers.CharField(source='stage.operation', read_only=True)
    order_item = serializers.SerializerMethodField()
    workshop_info = serializers.SerializerMethodField()
    is_completed = serializers.BooleanField(read_only=True)
    title = serializers.CharField(read_only=True)
    plan_quantity = serializers.IntegerField(read_only=True)
    started_at = serializers.DateTimeField(read_only=True)
    
    class Meta:
        model = EmployeeTask
        fields = [
            'id', 'stage', 'employee', 'employee_name', 'quantity', 'completed_quantity', 
            'defective_quantity', 'done_quantity', 'stage_name', 'order_item', 'workshop_info',
            'created_at', 'completed_at', 'earnings', 'penalties', 'net_earnings',
            'is_completed', 'title', 'plan_quantity', 'started_at'
        ]

    def get_done_quantity(self, obj):
        # Если задача выполнена, считаем всё количество сделанным, иначе 0
        return obj.quantity if getattr(obj, 'is_completed', False) else 0

    def get_employee_name(self, obj):
        if obj.employee:
            # Попробовать get_full_name, иначе first_name + last_name, иначе username
            if hasattr(obj.employee, 'get_full_name'):  
                name = obj.employee.get_full_name()
                if name:
                    return name
            first = getattr(obj.employee, 'first_name', '')
            last = getattr(obj.employee, 'last_name', '')
            if first or last:
                return f'{first} {last}'.strip()
            return getattr(obj.employee, 'username', str(obj.employee.pk))
        return ''
    
    def get_order_item(self, obj):
        """Возвращает сериализованный order_item с полной информацией о товаре"""
        print(f"=== DEBUG SERIALIZER: get_order_item for EmployeeTask {obj.id} ===")
        print(f"Stage: {obj.stage}")
        print(f"Stage order_item: {getattr(obj.stage, 'order_item', None) if obj.stage else None}")
        print(f"Stage order: {getattr(obj.stage, 'order', None) if obj.stage else None}")
        
        if obj.stage and obj.stage.order_item:
            # Если есть прямая связь с order_item
            print("Using direct order_item connection")
            from apps.orders.serializers import OrderItemSerializer
            result = OrderItemSerializer(obj.stage.order_item).data
            print(f"Direct order_item data: {result}")
            return result
        elif obj.stage and obj.stage.order:
            # Fallback: если order_item равен null, пытаемся получить данные через заказ
            print("Using fallback through order")
            from apps.orders.models import OrderItem
            from apps.orders.serializers import OrderItemSerializer
            
            # Ищем позиции заказа для этого заказа
            order_items = OrderItem.objects.filter(order=obj.stage.order)
            print(f"Found {order_items.count()} order items for order {obj.stage.order.id}")
            
            if order_items.exists():
                # Берем первую позицию (обычно их одна для простых заказов)
                first_item = order_items.first()
                print(f"Using first order item: {first_item}")
                item_data = OrderItemSerializer(first_item).data
                
                # Добавляем информацию о заказе
                item_data['order'] = {
                    'id': obj.stage.order.id,
                    'name': obj.stage.order.name,
                    'status': obj.stage.order.status,
                    'status_display': obj.stage.order.get_status_display(),
                    'created_at': obj.stage.order.created_at.isoformat() if obj.stage.order.created_at else None,
                    'client': {
                        'name': obj.stage.order.client.name if obj.stage.order.client else 'Не указан'
                    } if obj.stage.order.client else None
                }
                
                print(f"Fallback order_item data: {item_data}")
                return item_data
            else:
                print("No order items found for this order")
        else:
            print("No stage or order available")
        
        print("Returning None for order_item")
        return None
    
    def get_workshop_info(self, obj):
        """Возвращает информацию для цеха"""
        return obj.stage.get_workshop_info() if obj.stage else {} 