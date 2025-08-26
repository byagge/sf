from rest_framework import serializers
from .models import EmployeeTask, HelperTask
from apps.users.serializers import UserSerializer

class EmployeeTaskSerializer(serializers.ModelSerializer):
    employee = UserSerializer(read_only=True)
    title = serializers.ReadOnlyField()
    is_completed = serializers.ReadOnlyField()
    plan_quantity = serializers.ReadOnlyField()
    started_at = serializers.ReadOnlyField()
    stage_name = serializers.SerializerMethodField()
    order_item = serializers.SerializerMethodField()
    workshop_info = serializers.SerializerMethodField()
    
    class Meta:
        model = EmployeeTask
        fields = '__all__'

    def get_stage_name(self, obj):
        try:
            return obj.stage.operation if obj.stage else ''
        except Exception:
            return ''

    def get_order_item(self, obj):
        try:
            stage = getattr(obj, 'stage', None)
            order_item = getattr(stage, 'order_item', None) if stage else None
            if not order_item:
                return None
            # Собираем минимально необходимую структуру для фронтенда
            product = getattr(order_item, 'product', None)
            return {
                'id': getattr(order_item, 'id', None),
                'size': getattr(order_item, 'size', None),
                'color': getattr(order_item, 'color', None),
                'quantity': getattr(order_item, 'quantity', None),
                'paint_type': getattr(order_item, 'paint_type', None),
                'paint_color': getattr(order_item, 'paint_color', None),
                'glass_type_display': getattr(order_item, 'glass_type_display', None),
                'packaging_notes': getattr(order_item, 'packaging_notes', None),
                'cnc_specs': getattr(order_item, 'cnc_specs', None),
                'cutting_specs': getattr(order_item, 'cutting_specs', None),
                'product': None if not product else {
                    'id': getattr(product, 'id', None),
                    'name': getattr(product, 'name', None),
                    'img': getattr(product, 'img', None),
                    'is_glass': getattr(product, 'is_glass', False),
                    'type': getattr(product, 'type', None),
                    'description': getattr(product, 'description', None),
                    'price': getattr(product, 'price', None),
                }
            }
        except Exception:
            return None

    def get_workshop_info(self, obj):
        try:
            stage = getattr(obj, 'stage', None)
            workshop = getattr(stage, 'workshop', None) if stage else None
            if not workshop:
                return None
            return {
                'id': getattr(workshop, 'id', None),
                'name': getattr(workshop, 'name', None),
                'description': getattr(workshop, 'description', None),
                'cutting_specs': getattr(workshop, 'cutting_specs', None),
                'cnc_specs': getattr(workshop, 'cnc_specs', None),
                'paint_type': getattr(workshop, 'paint_type', None),
                'paint_color': getattr(workshop, 'paint_color', None),
            }
        except Exception:
            return None

class HelperTaskSerializer(serializers.ModelSerializer):
    helper = UserSerializer(read_only=True)
    employee_task = EmployeeTaskSerializer(read_only=True)
    title = serializers.ReadOnlyField()
    is_completed = serializers.ReadOnlyField()
    stage_name = serializers.ReadOnlyField()
    order_item = serializers.ReadOnlyField()
    workshop_info = serializers.ReadOnlyField()
    
    class Meta:
        model = HelperTask
        fields = '__all__'

class HelperTaskCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = HelperTask
        fields = ['employee_task', 'helper', 'quantity'] 