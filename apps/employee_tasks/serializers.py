from rest_framework import serializers
from .models import EmployeeTask, HelperTask
from apps.users.serializers import UserSerializer


def _safe_str(value):
    try:
        if isinstance(value, (bytes, bytearray)):
            return value.decode('utf-8', errors='ignore')
        return value
    except Exception:
        return ''

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

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Sanitize some common string fields if present
        for key in ['title', 'stage_name']:
            if key in data:
                data[key] = _safe_str(data.get(key))
        # Sanitize nested order_item
        if isinstance(data.get('order_item'), dict):
            for k in ['size', 'color', 'paint_type', 'paint_color', 'cnc_specs', 'cutting_specs', 'packaging_notes', 'glass_type_display']:
                if k in data['order_item']:
                    data['order_item'][k] = _safe_str(data['order_item'][k])
            if isinstance(data['order_item'].get('product'), dict):
                for k in ['name', 'type', 'description']:
                    if k in data['order_item']['product']:
                        data['order_item']['product'][k] = _safe_str(data['order_item']['product'][k])
                # Normalize img to URL/string
                if 'img' in data['order_item']['product']:
                    img = data['order_item']['product']['img']
                    try:
                        # If it's a FieldFile-like, prefer its url
                        url = getattr(img, 'url', None)
                        data['order_item']['product']['img'] = url or _safe_str(str(img)) if img is not None else None
                    except Exception:
                        data['order_item']['product']['img'] = None
        # Sanitize nested workshop_info
        if isinstance(data.get('workshop_info'), dict):
            for k in ['name', 'description']:
                if k in data['workshop_info']:
                    data['workshop_info'][k] = _safe_str(data['workshop_info'][k])
        return data

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
            # Normalize image to URL or string immediately to avoid passing FieldFile
            img_value = None
            if product is not None:
                try:
                    if getattr(product, 'img', None):
                        img_value = getattr(product.img, 'url', None) or _safe_str(str(product.img))
                except Exception:
                    img_value = None
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
                    'img': img_value,
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