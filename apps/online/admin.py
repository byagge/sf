from django.contrib import admin
from .models import UserActivity

@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = ('user', 'last_seen', 'is_online', 'user_email', 'user_full_name')
    list_filter = ('is_online', 'last_seen')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name')
    readonly_fields = ('last_seen',)
    ordering = ('-last_seen',)
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Email'
    
    def user_full_name(self, obj):
        full_name = f"{obj.user.first_name} {obj.user.last_name}".strip()
        return full_name if full_name else obj.user.username
    user_full_name.short_description = 'Полное имя'
    
    def has_add_permission(self, request):
        return False  # Запрещаем создание записей вручную
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser  # Только суперпользователи могут удалять
    
    actions = ['mark_offline', 'mark_online']
    
    def mark_offline(self, request, queryset):
        updated = queryset.update(is_online=False)
        self.message_user(request, f'{updated} пользователей отмечено как офлайн.')
    mark_offline.short_description = 'Отметить как офлайн'
    
    def mark_online(self, request, queryset):
        updated = queryset.update(is_online=True)
        self.message_user(request, f'{updated} пользователей отмечено как онлайн.')
    mark_online.short_description = 'Отметить как онлайн'
