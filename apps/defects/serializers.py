from rest_framework import serializers
from .models import Defect
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
            'id', 'product', 'product_id', 'user', 'user_id', 'workshop', 
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
    is_repairable = serializers.BooleanField(help_text='Можно ли починить брак')
    defect_type = serializers.ChoiceField(
        choices=Defect.DefectType.choices,
        required=False,
        allow_null=True,
        help_text='Тип брака (только если нельзя починить)'
    )
    target_workshop_id = serializers.PrimaryKeyRelatedField(
        queryset=Workshop.objects.all(),
        required=False,
        allow_null=True,
        help_text='Цех для исправления (только если нельзя починить)'
    )
    comment = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        help_text='Комментарий мастера'
    )

    def validate(self, data):
        is_repairable = data.get('is_repairable')
        defect_type = data.get('defect_type')
        target_workshop_id = data.get('target_workshop_id')
        
        if not is_repairable:
            if not defect_type:
                raise serializers.ValidationError(
                    "Тип брака обязателен, если брак нельзя починить"
                )
            if not target_workshop_id:
                raise serializers.ValidationError(
                    "Цех для исправления обязателен, если брак нельзя починить"
                )
        
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