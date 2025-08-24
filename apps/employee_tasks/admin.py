from django.contrib import admin
from .models import EmployeeTask, HelperTask

@admin.register(EmployeeTask)
class EmployeeTaskAdmin(admin.ModelAdmin):
    list_display = ['id', 'employee', 'stage', 'quantity', 'completed_quantity', 'defective_quantity', 'earnings', 'penalties', 'net_earnings', 'created_at']
    list_filter = ['created_at', 'completed_at', 'employee__workshop']
    search_fields = ['employee__first_name', 'employee__last_name', 'stage__operation']
    readonly_fields = ['earnings', 'penalties', 'net_earnings']

@admin.register(HelperTask)
class HelperTaskAdmin(admin.ModelAdmin):
    list_display = ['id', 'helper', 'employee_task', 'quantity', 'completed_quantity', 'defective_quantity', 'earnings', 'penalties', 'net_earnings', 'created_at']
    list_filter = ['created_at', 'completed_at', 'helper__workshop']
    search_fields = ['helper__first_name', 'helper__last_name', 'employee_task__stage__operation']
    readonly_fields = ['earnings', 'penalties', 'net_earnings']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('stage', 'employee', 'quantity')
        }),
        ('Выполнение', {
            'fields': ('completed_quantity', 'defective_quantity', 'completed_at')
        }),
        ('Финансы', {
            'fields': ('earnings', 'penalties', 'net_earnings'),
            'classes': ('collapse',)
        }),
        ('Система', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'employee', 'stage__workshop', 'stage__order'
        )
