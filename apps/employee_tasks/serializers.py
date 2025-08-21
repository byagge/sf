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
    stage = serializers.SerializerMethodField()
    
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
        if obj.stage and obj.stage.order_item:
            from apps.orders.serializers import OrderItemSerializer
            return OrderItemSerializer(obj.stage.order_item).data
        return None
    
    def get_stage(self, obj):
        """Возвращает полную информацию о stage с order_item и order"""
        if obj.stage:
            from apps.orders.serializers import OrderStageSerializer
            return OrderStageSerializer(obj.stage).data
        return None
    
    def get_workshop_info(self, obj):
        """Возвращает информацию для цеха"""
        return obj.stage.get_workshop_info() if obj.stage else {} 