from django.contrib import admin
from .models import EmployeeTask, HelperTask

@admin.register(EmployeeTask)
class EmployeeTaskAdmin(admin.ModelAdmin):
    list_display = ['employee', 'stage', 'quantity', 'completed_quantity', 'defective_quantity', 'earnings', 'net_earnings', 'created_at']
    list_filter = ['employee', 'stage__workshop', 'created_at', 'completed_at']
    search_fields = ['employee__first_name', 'employee__last_name', 'stage__operation']
    readonly_fields = ['earnings', 'penalties', 'net_earnings']
    date_hierarchy = 'created_at'

@admin.register(HelperTask)
class HelperTaskAdmin(admin.ModelAdmin):
    list_display = ['helper', 'employee_task', 'quantity', 'completed_quantity', 'defective_quantity', 'earnings', 'net_earnings', 'created_at']
    list_filter = ['helper', 'employee_task__stage__workshop', 'created_at', 'completed_at']
    search_fields = ['helper__first_name', 'helper__last_name', 'employee_task__employee__first_name', 'employee_task__employee__last_name']
    readonly_fields = ['earnings', 'penalties', 'net_earnings']
    date_hierarchy = 'created_at'
