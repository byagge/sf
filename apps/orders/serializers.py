from rest_framework import serializers
from .models import Order, OrderStage, OrderDefect, OrderItem, create_order_stages
from apps.clients.models import Client
from apps.products.models import Product
from apps.operations.workshops.models import Workshop

class SimpleEmployeeTaskSerializer(serializers.Serializer):
    """Упрощенный сериализатор для EmployeeTask без циклических ссылок"""
    id = serializers.IntegerField()
    employee = serializers.IntegerField()
    quantity = serializers.IntegerField()
    completed_quantity = serializers.IntegerField()
    defective_quantity = serializers.IntegerField()
    created_at = serializers.DateTimeField()
    completed_at = serializers.DateTimeField(allow_null=True)
    earnings = serializers.DecimalField(max_digits=10, decimal_places=2)
    penalties = serializers.DecimalField(max_digits=10, decimal_places=2)
    net_earnings = serializers.DecimalField(max_digits=10, decimal_places=2)
    stage_name = serializers.SerializerMethodField()
    is_completed = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()
    plan_quantity = serializers.SerializerMethodField()
    started_at = serializers.SerializerMethodField()
    
    def get_stage_name(self, obj):
        """Возвращает название этапа"""
        return obj.stage.operation if obj.stage else ''
    
    def get_is_completed(self, obj):
        """Проверяет, выполнена ли задача полностью"""
        return obj.completed_quantity >= obj.quantity
    
    def get_title(self, obj):
        """Возвращает название задачи на основе этапа"""
        if obj.stage:
            return f"{obj.stage.operation} - {obj.stage.order.name if obj.stage.order else 'Заказ'}"
        return f"Задача #{obj.id}"
    
    def get_plan_quantity(self, obj):
        """Возвращает план задачи"""
        return obj.quantity
    
    def get_started_at(self, obj):
        """Возвращает дату начала задачи"""
        return obj.created_at

class ClientFullSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ['id', 'name', 'company', 'phone', 'email', 'address', 'created_at', 'updated_at']

class ProductFullSerializer(serializers.ModelSerializer):
    glass_type_display = serializers.CharField(source='get_glass_type_display', read_only=True)
    
    class Meta:
        model = Product
        fields = ['id', 'name', 'type', 'description', 'is_glass', 'glass_type', 'glass_type_display', 'img', 'price', 'created_at', 'updated_at']

class WorkshopFullSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workshop
        fields = ['id', 'name', 'description', 'is_active', 'created_at', 'updated_at']

class WorkshopShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workshop
        fields = ['id', 'name']

class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductFullSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all(), write_only=True, source='product')
    glass_type_display = serializers.CharField(source='get_glass_type_display', read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            'id', 'product', 'product_id', 'quantity', 'size', 'color',
            'glass_type', 'glass_type_display', 'paint_type', 'paint_color',
            'cnc_specs', 'cutting_specs', 'packaging_notes',
            'glass_cutting_completed', 'glass_cutting_quantity', 'packaging_received_quantity'
        ]

class OrderStageSerializer(serializers.ModelSerializer):
    workshop = WorkshopShortSerializer(read_only=True)
    assigned = SimpleEmployeeTaskSerializer(source='employee_tasks', many=True, read_only=True)
    order_name = serializers.CharField(source='order.name', read_only=True)
    order_item = OrderItemSerializer(read_only=True)
    order = serializers.SerializerMethodField()
    done_count = serializers.IntegerField(read_only=True)
    defective_count = serializers.IntegerField(read_only=True)
    workshop_info = serializers.SerializerMethodField()
    
    class Meta:
        model = OrderStage
        fields = [
            'id', 'workshop', 'order_name', 'order_item', 'order', 'operation', 'sequence', 
            'parallel_group', 'plan_quantity', 'completed_quantity', 'done_count', 
            'defective_count', 'deadline', 'status', 'in_progress', 'defective', 
            'completed', 'date', 'comment', 'assigned', 'workshop_info'
        ]
    
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
    
    def get_workshop_info(self, obj):
        """Возвращает информацию для цеха"""
        return obj.get_workshop_info()

class OrderDefectSerializer(serializers.ModelSerializer):
    workshop = WorkshopFullSerializer(read_only=True)
    class Meta:
        model = OrderDefect
        fields = ['id', 'workshop', 'quantity', 'date', 'comment']

class OrderSerializer(serializers.ModelSerializer):
    client = ClientFullSerializer(read_only=True)
    product = ProductFullSerializer(read_only=True)
    client_id = serializers.PrimaryKeyRelatedField(queryset=Client.objects.all(), write_only=True, source='client')
    product_id = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all(), write_only=True, source='product', required=False, allow_null=True)
    workshop = WorkshopFullSerializer(read_only=True)
    stages = OrderStageSerializer(many=True, read_only=True)
    defects = OrderDefectSerializer(source='order_defects', many=True, read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    items_data = OrderItemSerializer(many=True, write_only=True, required=False, source='items')
    total_done_count = serializers.IntegerField(read_only=True)
    total_defective_count = serializers.IntegerField(read_only=True)
    status_display = serializers.CharField(read_only=True)
    total_quantity = serializers.IntegerField(read_only=True)
    has_glass_items = serializers.BooleanField(read_only=True)
    glass_items = serializers.SerializerMethodField()
    regular_items = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'name', 'client', 'client_id', 'workshop', 'product', 'product_id', 
            'quantity', 'status', 'status_display', 'expenses', 'comment', 'created_at', 
            'stages', 'defects', 'items', 'items_data', 'total_done_count', 
            'total_defective_count', 'total_quantity', 'has_glass_items', 'glass_items', 'regular_items'
        ]

    def get_glass_items(self, obj):
        return [OrderItemSerializer(item).data for item in obj.glass_items]

    def get_regular_items(self, obj):
        return [OrderItemSerializer(item).data for item in obj.regular_items]

    def validate(self, attrs):
        # Allow either legacy product/quantity or items list
        items = self.initial_data.get('items') or self.initial_data.get('items_data')
        product = attrs.get('product')
        quantity = attrs.get('quantity')
        if not items and not (product and quantity):
            raise serializers.ValidationError('Нужно указать либо product_id и quantity, либо список items.')
        return attrs

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        order = Order.objects.create(**validated_data)
        # If items provided, create them; otherwise legacy single product mapping as one item for consistency
        if items_data:
            for item in items_data:
                OrderItem.objects.create(order=order, **item)
            # Ensure stages exist now that we know total quantity
            if not order.stages.exists():
                create_order_stages(order)
        elif order.product and order.quantity:
            OrderItem.objects.create(order=order, product=order.product, quantity=order.quantity)
        return order

class OrderStageConfirmSerializer(serializers.Serializer):
    completed_quantity = serializers.IntegerField(min_value=0) 