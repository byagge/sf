from django.contrib import admin
from .models import Workshop

@admin.register(Workshop)
class WorkshopAdmin(admin.ModelAdmin):
    list_display = ['name', 'manager', 'description', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'manager__first_name', 'manager__last_name']
