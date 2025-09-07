from django.contrib import admin
from .models import Service, ServiceMaterial

class ServiceMaterialInline(admin.TabularInline):
    model = ServiceMaterial
    extra = 1

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'unit', 'is_active', 'created_at', 'updated_at')
    search_fields = ('name', 'code', 'description')
    list_filter = ('is_active', 'unit')
    ordering = ('name',)
    inlines = [ServiceMaterialInline]

@admin.register(ServiceMaterial)
class ServiceMaterialAdmin(admin.ModelAdmin):
    list_display = ('service', 'material', 'amount')
    search_fields = ('service__name', 'material__name')
    list_filter = ('service', 'material')
