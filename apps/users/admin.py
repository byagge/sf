from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from apps.users.models import User

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        (None, {'fields': (
            'role', 'phone', 'workshop',
            'passport_number', 'inn', 'employment_date', 'fired_date', 'contract_number', 'notes',
        )}),
    )
    list_display = (
        'username', 'get_full_name', 'role', 'phone', 'workshop',
        'employment_date', 'fired_date', 'is_active', 'is_staff'
    )
    list_filter = ('role', 'workshop', 'is_active', 'is_staff', 'employment_date', 'fired_date')
    search_fields = ('username', 'first_name', 'last_name', 'phone', 'passport_number', 'inn', 'contract_number')
    
    def get_full_name(self, obj):
        """Отображает полное имя в списке"""
        return obj.get_full_name()
    get_full_name.short_description = 'ФИО'
    get_full_name.admin_order_field = 'last_name'
