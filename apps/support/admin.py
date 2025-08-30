from django.contrib import admin
from django.utils.html import format_html
from .models import SupportChat, ChatMessage, AIUserSettings, SupportCategory, SupportTicket

@admin.register(SupportChat)
class SupportChatAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'title', 'is_active', 'created_at', 'message_count']
    list_filter = ['is_active', 'created_at']
    search_fields = ['user__username', 'user__email', 'title']
    readonly_fields = ['created_at', 'updated_at']
    
    def message_count(self, obj):
        return obj.messages.count()
    message_count.short_description = 'Количество сообщений'

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'chat', 'message_type', 'content_preview', 'created_at']
    list_filter = ['message_type', 'created_at']
    search_fields = ['content', 'chat__user__username']
    readonly_fields = ['created_at']
    
    def content_preview(self, obj):
        return obj.content[:100] + '...' if len(obj.content) > 100 else obj.content
    content_preview.short_description = 'Содержание'

@admin.register(AIUserSettings)
class AIUserSettingsAdmin(admin.ModelAdmin):
    list_display = ['user', 'ai_enabled', 'ai_model', 'max_tokens', 'temperature', 'updated_at']
    list_filter = ['ai_enabled', 'ai_model']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at']
    actions = ['enable_ai', 'disable_ai']
    
    def enable_ai(self, request, queryset):
        queryset.update(ai_enabled=True)
    enable_ai.short_description = 'Включить ИИ для выбранных пользователей'
    
    def disable_ai(self, request, queryset):
        queryset.update(ai_enabled=False)
    disable_ai.short_description = 'Отключить ИИ для выбранных пользователей'

@admin.register(SupportCategory)
class SupportCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'description']

@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ['id', 'chat_user', 'category', 'priority', 'status', 'assigned_admin', 'created_at']
    list_filter = ['priority', 'status', 'category', 'created_at']
    search_fields = ['chat__user__username', 'chat__user__email']
    readonly_fields = ['created_at', 'updated_at']
    list_editable = ['priority', 'status', 'assigned_admin']
    
    def chat_user(self, obj):
        return obj.chat.user.username
    chat_user.short_description = 'Пользователь'
