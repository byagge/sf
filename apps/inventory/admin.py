from django.contrib import admin
from .models import RawMaterial, MaterialIncoming, MaterialConsumption

class RawMaterialAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'quantity', 'unit', 'price', 'total_value', 'min_quantity', 'created_at']
    list_filter = ['unit', 'created_at']
    search_fields = ['name', 'code', 'description']
    readonly_fields = ['code', 'total_value', 'created_at', 'updated_at']
    ordering = ['name']
    
    def get_readonly_fields(self, request, obj=None):
        # Если это создание нового объекта, код не редактируем
        if obj is None:
            return ['code', 'total_value', 'created_at', 'updated_at']
        # Если это редактирование существующего, код не редактируем
        return ['code', 'total_value', 'created_at', 'updated_at']

admin.site.register(RawMaterial, RawMaterialAdmin)

class MaterialIncomingAdmin(admin.ModelAdmin):
    list_display = ['material', 'quantity', 'price_per_unit', 'total_value', 'created_at']
    list_filter = ['created_at', 'material']
    search_fields = ['material__name', 'material__code', 'notes']
    readonly_fields = ['total_value', 'created_at']
    ordering = ['-created_at']

admin.site.register(MaterialIncoming, MaterialIncomingAdmin) 

@admin.register(MaterialConsumption)
class MaterialConsumptionAdmin(admin.ModelAdmin):
    list_display = ['material', 'quantity', 'workshop', 'order', 'consumed_at']
    list_filter = ['consumed_at', 'workshop', 'material']
    search_fields = ['material__name', 'workshop__name', 'order__name']
    readonly_fields = ['consumed_at']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('material', 'quantity', 'workshop', 'order')
        }),
        ('Система', {
            'fields': ('employee_task', 'consumed_at'),
            'classes': ('collapse',)
        }),
    ) 