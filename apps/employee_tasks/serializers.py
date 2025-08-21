from rest_framework import serializers
from .models import EmployeeTask

class SimpleOrderStageSerializer(serializers.Serializer):
    """Упрощенный сериализатор для OrderStage без циклических ссылок"""
    id = serializers.IntegerField()
    operation = serializers.CharField()
    sequence = serializers.IntegerField()
    plan_quantity = serializers.IntegerField()
    completed_quantity = serializers.IntegerField()
    status = serializers.CharField()
    deadline = serializers.DateField(allow_null=True)
    parallel_group = serializers.IntegerField(allow_null=True)
    in_progress = serializers.SerializerMethodField()
    defective = serializers.SerializerMethodField()
    completed = serializers.SerializerMethodField()
    date = serializers.SerializerMethodField()
    comment = serializers.CharField()
    done_count = serializers.SerializerMethodField()
    defective_count = serializers.SerializerMethodField()
    order_item = serializers.SerializerMethodField()
    order = serializers.SerializerMethodField()
    workshop = serializers.SerializerMethodField()
    workshop_info = serializers.SerializerMethodField()
    
    def get_date(self, obj):
        """Возвращает дату этапа"""
        return getattr(obj, 'date', None)
    
    def get_in_progress(self, obj):
        """Возвращает количество задач в работе"""
        return getattr(obj, 'in_progress', 0)
    
    def get_defective(self, obj):
        """Возвращает количество брака"""
        return getattr(obj, 'defective', 0)
    
    def get_completed(self, obj):
        """Возвращает количество завершенных задач"""
        return getattr(obj, 'completed', 0)
    
    def get_done_count(self, obj):
        """Возвращает количество выполненных задач"""
        return sum(task.completed_quantity for task in obj.employee_tasks.all())
    
    def get_defective_count(self, obj):
        """Возвращает количество брака"""
        return sum(task.defective_quantity for task in obj.employee_tasks.all())
    
    def get_order_item(self, obj):
        """Возвращает сериализованный order_item"""
        if obj.order_item:
            from apps.orders.serializers import OrderItemSerializer
            return OrderItemSerializer(obj.order_item).data
        return None
    
    def get_order(self, obj):
        """Возвращает информацию о заказе"""
        if obj.order:
            return {
                'id': obj.order.id,
                'name': obj.order.name,
                'status': obj.order.status,
                'status_display': obj.order.status_display,
                'client': {
                    'id': obj.order.client.id,
                    'name': obj.order.client.name
                } if obj.order.client else None,
                'created_at': obj.order.created_at.isoformat() if obj.order.created_at else None
            }
        return None
    
    def get_workshop(self, obj):
        """Возвращает информацию о цехе"""
        if obj.workshop:
            return {
                'id': obj.workshop.id,
                'name': obj.workshop.name
            }
        return None
    
    def get_workshop_info(self, obj):
        """Возвращает информацию для цеха"""
        return obj.get_workshop_info() if hasattr(obj, 'get_workshop_info') else {}

class EmployeeTaskSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    done_quantity = serializers.SerializerMethodField()
    stage_name = serializers.CharField(source='stage.operation', read_only=True)
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
            'defective_quantity', 'done_quantity', 'stage_name', 'workshop_info',
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
    
    def get_stage(self, obj):
        """Возвращает полную информацию о stage с order_item и order"""
        if obj.stage:
            return SimpleOrderStageSerializer(obj.stage).data
        return None
    
    def get_workshop_info(self, obj):
        """Возвращает информацию для цеха"""
        return obj.stage.get_workshop_info() if obj.stage else {} 