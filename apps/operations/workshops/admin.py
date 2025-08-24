from django.contrib import admin
from django.utils.html import format_html
from .models import Workshop, WorkshopMaster

class WorkshopMasterInline(admin.TabularInline):
    model = WorkshopMaster
    extra = 1
    fields = ['master', 'is_active', 'notes']
    autocomplete_fields = ['master']
    
    def get_queryset(self, request):
        return super().get_queryset(request).filter(is_active=True)

@admin.register(Workshop)
class WorkshopAdmin(admin.ModelAdmin):
    list_display = ['name', 'manager', 'additional_masters_display', 'description', 'is_active']
    list_filter = ['is_active', 'manager']
    search_fields = ['name', 'manager__first_name', 'manager__last_name']
    autocomplete_fields = ['manager']
    inlines = [WorkshopMasterInline]
    
    def additional_masters_display(self, obj):
        """Отображает дополнительных мастеров цеха"""
        additional_masters = obj.workshop_masters.filter(is_active=True)
        if additional_masters.exists():
            master_names = [wm.master.get_full_name() for wm in additional_masters]
            return format_html('<span style="color: #666;">{}</span>', ', '.join(master_names))
        return format_html('<span style="color: #999;">Нет</span>')
    
    additional_masters_display.short_description = 'Дополнительные мастера'
    
    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('workshop_masters__master')

@admin.register(WorkshopMaster)
class WorkshopMasterAdmin(admin.ModelAdmin):
    list_display = ['workshop', 'master', 'is_active', 'added_at', 'added_by']
    list_filter = ['is_active', 'added_at', 'workshop']
    search_fields = ['workshop__name', 'master__first_name', 'master__last_name', 'master__username']
    autocomplete_fields = ['workshop', 'master', 'added_by']
    readonly_fields = ['added_at']
    
    def save_model(self, request, obj, form, change):
        if not change:  # Только при создании
            obj.added_by = request.user
        super().save_model(request, obj, form, change)
