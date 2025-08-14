from rest_framework import serializers
from .models import Defect, DefectRepairTask
from apps.products.models import Product
from apps.users.models import User
from apps.operations.workshops.models import Workshop

class ProductShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name']

class UserShortSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    class Meta:
        model = User
        fields = ['id', 'full_name']
    def get_full_name(self, obj):
        return obj.get_full_name()

class WorkshopShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workshop
        fields = ['id', 'name']

class DefectSerializer(serializers.ModelSerializer):
    product = ProductShortSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all(), source='product', write_only=True)
    user = UserShortSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), source='user', write_only=True)
    workshop = serializers.SerializerMethodField()
    master_confirmed_by = UserShortSerializer(read_only=True)
    target_workshop = WorkshopShortSerializer(read_only=True)
    target_workshop_id = serializers.PrimaryKeyRelatedField(
        queryset=Workshop.objects.all(), 
        source='target_workshop', 
        write_only=True,
        required=False,
        allow_null=True
    )

    class Meta:
        model = Defect
        fields = [
            'id', 'product', 'product_id', 'user', 'user_id', 'workshop', 
            'created_at', 'status', 'defect_type', 'can_be_fixed', 
            'target_workshop', 'target_workshop_id', 'master_confirmed_by',
            'master_confirmed_at', 'notes'
        ]
        read_only_fields = ['id', 'created_at', 'workshop', 'user', 'master_confirmed_by', 'master_confirmed_at']

    def get_workshop(self, obj):
        workshop = obj.get_workshop()
        if workshop:
            return WorkshopShortSerializer(workshop).data
        return None

class DefectRepairTaskSerializer(serializers.ModelSerializer):
    defect = DefectSerializer(read_only=True)
    assigned_to = UserShortSerializer(read_only=True)
    workshop = WorkshopShortSerializer(read_only=True)
    
    class Meta:
        model = DefectRepairTask
        fields = [
            'id', 'defect', 'assigned_to', 'workshop', 'status', 'title',
            'description', 'priority', 'created_at', 'started_at', 'completed_at',
            'estimated_hours', 'actual_hours', 'notes'
        ]
        read_only_fields = ['id', 'created_at', 'started_at', 'completed_at']

class DefectMasterReviewSerializer(serializers.Serializer):
    """Сериализатор для подтверждения брака мастером"""
    can_be_fixed = serializers.BooleanField(help_text='Можно ли починить брак')
    defect_type = serializers.ChoiceField(
        choices=Defect.DefectType.choices,
        required=False,
        help_text='Тип брака (только если нельзя починить)'
    )
    target_workshop_id = serializers.PrimaryKeyRelatedField(
        queryset=Workshop.objects.all(),
        required=False,
        help_text='Цех для восстановления (только если можно починить)'
    )
    notes = serializers.CharField(required=False, help_text='Примечания')

class DefectRepairTaskCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания задачи по восстановлению брака"""
    defect_id = serializers.PrimaryKeyRelatedField(
        queryset=Defect.objects.all(),
        source='defect',
        help_text='ID брака'
    )
    workshop_id = serializers.PrimaryKeyRelatedField(
        queryset=Workshop.objects.all(),
        source='workshop',
        help_text='ID цеха'
    )
    assigned_to_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role='worker'),
        source='assigned_to',
        required=False,
        help_text='ID сотрудника для назначения задачи'
    )
    
    class Meta:
        model = DefectRepairTask
        fields = [
            'defect_id', 'workshop_id', 'assigned_to_id', 'title', 'description',
            'priority', 'estimated_hours', 'notes'
        ] 