from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    is_helper = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'first_name', 'last_name', 'email', 'phone',
            'role', 'workshop', 'full_name', 'is_helper'
        ]
        read_only_fields = ['id', 'username', 'full_name', 'is_helper']

    def get_full_name(self, obj):
        if hasattr(obj, 'get_full_name'):
            return obj.get_full_name()
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username

    def get_is_helper(self, obj):
        return getattr(obj, 'is_helper', lambda: False)() 