from django.contrib import admin
from .models import Defect, DefectRepairTask

@admin.register(Defect)
class DefectAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'status', 'defect_type', 'created_at', 'master_confirmed_by']
    list_filter = ['status', 'defect_type', 'created_at', 'master_confirmed_at']
    search_fields = ['product__name', 'user__username', 'user__first_name', 'user__last_name']
    readonly_fields = ['created_at', 'master_confirmed_at', 'fixed_at']
    fieldsets = (
        ('Основная информация', {
            'fields': ('product', 'user', 'created_at', 'status')
        }),
        ('Проверка мастером', {
            'fields': ('master_confirmed_by', 'master_confirmed_at', 'can_be_fixed')
        }),
        ('Классификация', {
            'fields': ('defect_type', 'target_workshop')
        }),
        ('Исправление', {
            'fields': ('fixed_by', 'fixed_at')
        }),
        ('Дополнительно', {
            'fields': ('notes',)
        }),
    )

@admin.register(DefectRepairTask)
class DefectRepairTaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'defect', 'workshop', 'assigned_to', 'status', 'priority', 'created_at']
    list_filter = ['status', 'priority', 'workshop', 'created_at']
    search_fields = ['title', 'defect__product__name', 'assigned_to__username']
    readonly_fields = ['created_at', 'started_at', 'completed_at']
    fieldsets = (
        ('Основная информация', {
            'fields': ('defect', 'workshop', 'title', 'description', 'priority')
        }),
        ('Назначение', {
            'fields': ('assigned_to', 'status')
        }),
        ('Временные рамки', {
            'fields': ('created_at', 'started_at', 'completed_at', 'estimated_hours', 'actual_hours')
        }),
        ('Дополнительно', {
            'fields': ('notes',)
        }),
    ) 