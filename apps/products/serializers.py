from rest_framework import serializers
from .models import Product, MaterialConsumption
from apps.services.models import Service
from apps.inventory.models import RawMaterial

class ServiceShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ('id', 'name')

class MaterialConsumptionSerializer(serializers.ModelSerializer):
    material_name = serializers.CharField(source='material.name', read_only=True)
    material_unit = serializers.CharField(source='material.unit', read_only=True)
    material_id = serializers.PrimaryKeyRelatedField(queryset=RawMaterial.objects.all(), source='material', write_only=True)

    class Meta:
        model = MaterialConsumption
        fields = ['id', 'material_id', 'material_name', 'material_unit', 'amount', 'workshop']
        extra_kwargs = {'workshop': {'required': False}}

class ProductSerializer(serializers.ModelSerializer):
    services = ServiceShortSerializer(many=True, read_only=True)
    service_ids = serializers.PrimaryKeyRelatedField(
        queryset=Service.objects.all(), many=True, write_only=True, source='services'
    )
    materials = serializers.SerializerMethodField()
    cost_price = serializers.SerializerMethodField()
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    materials_consumption = MaterialConsumptionSerializer(many=True, source='materialconsumption_set', required=False)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'type', 'type_display', 'description', 'is_glass', 'img', 'price',
            'services', 'service_ids', 'materials', 'cost_price',
            'materials_consumption',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'services', 'materials', 'cost_price', 'type_display']

    def get_materials(self, obj):
        result = []
        for material, amount in obj.get_materials_with_amounts().items():
            result.append({
                'id': material.id,
                'name': material.name,
                'amount': amount,
                'unit': material.unit,
                'price': float(material.price),
            })
        return result

    def get_cost_price(self, obj):
        return obj.get_cost_price()

    def update(self, instance, validated_data):
        # Обновляем основные поля
        services = validated_data.pop('services', None)
        materials_data = validated_data.pop('materialconsumption_set', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if services is not None:
            instance.services.set(services)
        instance.save()
        # Обновляем материалы
        if materials_data is not None:
            instance.materialconsumption_set.all().delete()
            for mat in materials_data:
                MaterialConsumption.objects.create(product=instance, **mat)
        return instance

    def create(self, validated_data):
        services = validated_data.pop('services', None)
        materials_data = validated_data.pop('materialconsumption_set', None)
        product = Product.objects.create(**validated_data)
        if services is not None:
            product.services.set(services)
        if materials_data is not None:
            for mat in materials_data:
                MaterialConsumption.objects.create(product=product, **mat)
        return product 