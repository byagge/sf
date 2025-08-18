from rest_framework import serializers
from .models import Defect
from apps.products.models import Product
from apps.users.models import User
from apps.operations.workshops.models import Workshop
from apps.employee_tasks.models import EmployeeTask

class ProductShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name', 'code']

class UserShortSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'full_name']
    
    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username

class WorkshopShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workshop
        fields = ['id', 'name']

class EmployeeTaskShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeTask
        fields = ['id', 'stage', 'employee']

class DefectSerializer(serializers.ModelSerializer):
    product = ProductShortSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all(), source='product', write_only=True)
    user = UserShortSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), source='user', write_only=True)
    employee_task = EmployeeTaskShortSerializer(read_only=True)
    employee_task_id = serializers.PrimaryKeyRelatedField(
        queryset=EmployeeTask.objects.all(), 
        source='employee_task', 
        write_only=True
    )
    workshop = serializers.SerializerMethodField()
    confirmed_by = UserShortSerializer(read_only=True)
    target_workshop = WorkshopShortSerializer(read_only=True)
    target_workshop_id = serializers.PrimaryKeyRelatedField(
        queryset=Workshop.objects.all(), 
        source='target_workshop', 
        write_only=True,
        required=False,
        allow_null=True
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    defect_type_display = serializers.CharField(source='get_defect_type_display', read_only=True)

    class Meta:
        model = Defect
        fields = [
            'id', 'employee_task', 'employee_task_id', 'product', 'product_id', 'user', 'user_id', 'workshop', 
            'created_at', 'status', 'status_display', 'defect_type', 'defect_type_display',
            'confirmed_by', 'confirmed_at', 'is_repairable', 'target_workshop', 
            'target_workshop_id', 'transferred_at', 'master_comment', 'repair_comment',
            'penalty_amount', 'penalty_applied'
        ]
        read_only_fields = [
            'id', 'created_at', 'workshop', 'user', 'status', 'confirmed_by', 
            'confirmed_at', 'penalty_amount', 'penalty_applied'
        ]

    def get_workshop(self, obj):
        workshop = obj.get_workshop()
        if workshop:
            return WorkshopShortSerializer(workshop).data
        return None

class DefectConfirmationSerializer(serializers.Serializer):
    is_repairable = serializers.BooleanField(required=True)
    defect_type = serializers.ChoiceField(
        choices=Defect.DefectType.choices,
        required=False,
        allow_null=True
    )
    target_workshop_id = serializers.PrimaryKeyRelatedField(
        queryset=Workshop.objects.all(),
        required=False,
        allow_null=True
    )
    comment = serializers.CharField(max_length=500, required=False, allow_blank=True)

    def validate(self, data):
        is_repairable = data.get('is_repairable')
        defect_type = data.get('defect_type')
        target_workshop_id = data.get('target_workshop_id')
        
        # Если брак нельзя починить, должен быть указан тип брака
        if not is_repairable and not defect_type:
            raise serializers.ValidationError("Для неисправимого брака должен быть указан тип брака")
        
        # Если указан целевой цех, брак должен быть неисправимым
        if target_workshop_id and is_repairable:
            raise serializers.ValidationError("Целевой цех может быть указан только для неисправимого брака")
        
        return data

class DefectRepairSerializer(serializers.Serializer):
    comment = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        help_text='Комментарий по починке'
    )

class DefectListSerializer(serializers.ModelSerializer):
    """Сериализатор для списка браков с фильтрацией по мастеру"""
    product = ProductShortSerializer(read_only=True)
    user = UserShortSerializer(read_only=True)
    workshop = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    defect_type_display = serializers.CharField(source='get_defect_type_display', read_only=True)
    confirmed_by = UserShortSerializer(read_only=True)
    target_workshop = WorkshopShortSerializer(read_only=True)

    class Meta:
        model = Defect
        fields = [
            'id', 'product', 'user', 'workshop', 'created_at', 'status', 
            'status_display', 'defect_type', 'defect_type_display', 'confirmed_by',
            'confirmed_at', 'is_repairable', 'target_workshop', 'transferred_at',
            'master_comment', 'penalty_amount', 'penalty_applied'
        ]

    def get_workshop(self, obj):
        workshop = obj.get_workshop()
        if workshop:
            return WorkshopShortSerializer(workshop).data
        return None 