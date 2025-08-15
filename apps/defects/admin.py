from django.contrib import admin
from .models import Defect

@admin.register(Defect)
class DefectAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'product', 'user', 'status', 'defect_type', 
        'confirmed_by', 'created_at', 'confirmed_at'
    ]
    list_filter = [
        'status', 'defect_type', 'created_at', 'confirmed_at',
        'user__workshop', 'target_workshop'
    ]
    search_fields = [
        'product__name', 'user__first_name', 'user__last_name',
        'confirmed_by__first_name', 'confirmed_by__last_name'
    ]
    readonly_fields = [
        'created_at', 'confirmed_at', 'transferred_at', 'penalty_amount'
    ]
    fieldsets = (
        ('Основная информация', {
            'fields': ('product', 'user', 'created_at', 'status')
        }),
        ('Подтверждение мастером', {
            'fields': ('confirmed_by', 'confirmed_at', 'is_repairable', 'master_comment')
        }),
        ('Детали брака', {
            'fields': ('defect_type', 'target_workshop', 'transferred_at')
        }),
        ('Починка', {
            'fields': ('repair_task', 'repair_comment')
        }),
        ('Штрафы', {
            'fields': ('penalty_amount', 'penalty_applied')
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'product', 'user', 'confirmed_by', 'target_workshop', 'repair_task'
        ) 