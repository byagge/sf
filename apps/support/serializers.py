from rest_framework import serializers
from .models import SupportChat, ChatMessage, AIUserSettings, SupportCategory, SupportTicket
from django.contrib.auth import get_user_model

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']

class SupportCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportCategory
        fields = ['id', 'name', 'description']

class ChatMessageSerializer(serializers.ModelSerializer):
    message_type_display = serializers.CharField(source='get_message_type_display', read_only=True)
    created_at_formatted = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatMessage
        fields = ['id', 'chat', 'message_type', 'message_type_display', 'content', 'created_at', 'created_at_formatted']
        read_only_fields = ['created_at']
    
    def get_created_at_formatted(self, obj):
        return obj.created_at.strftime('%d.%m.%Y %H:%M')

class SupportChatSerializer(serializers.ModelSerializer):
    messages = ChatMessageSerializer(many=True, read_only=True)
    user = UserSerializer(read_only=True)
    message_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    
    class Meta:
        model = SupportChat
        fields = ['id', 'user', 'title', 'is_active', 'created_at', 'updated_at', 'messages', 'message_count', 'last_message']
        read_only_fields = ['created_at', 'updated_at']
    
    def get_message_count(self, obj):
        return obj.messages.count()
    
    def get_last_message(self, obj):
        last_msg = obj.messages.last()
        if last_msg:
            return {
                'content': last_msg.content[:100] + '...' if len(last_msg.content) > 100 else last_msg.content,
                'type': last_msg.message_type,
                'created_at': last_msg.created_at.strftime('%d.%m.%Y %H:%M')
            }
        return None

class AIUserSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIUserSettings
        fields = ['id', 'user', 'ai_enabled', 'ai_model', 'max_tokens', 'temperature']
        read_only_fields = ['user']

class SupportTicketSerializer(serializers.ModelSerializer):
    chat = SupportChatSerializer(read_only=True)
    category = SupportCategorySerializer(read_only=True)
    assigned_admin = UserSerializer(read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = SupportTicket
        fields = ['id', 'chat', 'category', 'priority', 'priority_display', 'status', 'status_display', 
                 'assigned_admin', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

class CreateChatSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportChat
        fields = ['title']

class SendMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ['content'] 