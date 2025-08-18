from django.contrib import admin
from .models import FinishedGood

@admin.register(FinishedGood)
class FinishedGoodAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'order_item', 'quantity', 'order', 'status', 'workshop', 'received_at', 'issued_at', 'recipient')
    list_filter = ('status', 'product', 'order', 'workshop', 'received_at', 'issued_at', 'quality_check_passed')
    search_fields = ('product__name', 'order__name', 'order_item__size', 'order_item__color', 'recipient', 'comment')
    readonly_fields = ('received_at', 'issued_at', 'packaging_date')
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('product', 'order_item', 'order', 'quantity')
        }),
        ('Статус и размещение', {
            'fields': ('status', 'workshop', 'quality_check_passed')
        }),
        ('Даты', {
            'fields': ('received_at', 'packaging_date', 'issued_at'),
            'classes': ('collapse',)
        }),
        ('Выдача', {
            'fields': ('recipient', 'comment'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_quality_checked', 'mark_as_issued']
    
    def mark_as_quality_checked(self, request, queryset):
        """Отметить выбранные товары как прошедшие проверку качества"""
        updated = queryset.update(quality_check_passed=True)
        self.message_user(request, f'Проверка качества пройдена для {updated} товаров')
    mark_as_quality_checked.short_description = 'Отметить как прошедшие проверку качества'
    
    def mark_as_issued(self, request, queryset):
        """Отметить выбранные товары как выданные"""
        from django.utils import timezone
        updated = queryset.filter(status='stock').update(
            status='issued',
            issued_at=timezone.now(),
            recipient='Выдано через админку'
        )
        self.message_user(request, f'Отмечено как выданные {updated} товаров')
    mark_as_issued.short_description = 'Отметить как выданные'
