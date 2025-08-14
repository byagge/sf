from rest_framework import serializers
from .models import FinishedGood
from apps.products.serializers import ProductSerializer
from apps.orders.serializers import OrderSerializer

class FinishedGoodSerializer(serializers.ModelSerializer):
    product = serializers.StringRelatedField()
    order = serializers.StringRelatedField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = FinishedGood
        fields = [
            'id', 'product', 'quantity', 'order', 'status', 'status_display',
            'received_at', 'issued_at', 'recipient', 'comment'
        ]

class FinishedGoodDetailSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    order = OrderSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = FinishedGood
        fields = [
            'id', 'product', 'quantity', 'order', 'status', 'status_display',
            'received_at', 'issued_at', 'recipient', 'comment'
        ] 