from django.contrib import admin
from .models import Order, OrderStage, OrderDefect, OrderItem

class OrderStageInline(admin.TabularInline):
    model = OrderStage
    extra = 1
    fields = ('stage_type', 'workshop', 'finished_good', 'in_progress', 'completed', 'defective', 'date', 'comment')
    readonly_fields = ('date',)

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1
    fields = ('product', 'quantity', 'size', 'color')

class OrderDefectInline(admin.TabularInline):
    model = OrderDefect
    extra = 0
    fields = ('workshop', 'quantity', 'date', 'comment')
    readonly_fields = ('date',)

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'client', 'get_workshop', 'product', 'quantity', 'get_total_quantity', 'status', 'expenses', 'created_at')
    list_filter = ('status', 'workshop', 'client', 'product', 'created_at')
    search_fields = ('name', 'client__name', 'product__name', 'comment', 'workshop__name')
    readonly_fields = ('expenses', 'created_at')
    inlines = [OrderItemInline, OrderStageInline, OrderDefectInline]

    def get_workshop(self, obj):
        return obj.workshop.__str__() if obj.workshop else ''
    get_workshop.short_description = 'Этап (цех)'

    def get_total_quantity(self, obj):
        return obj.total_quantity
    get_total_quantity.short_description = 'Итого шт.'

@admin.register(OrderStage)
class OrderStageAdmin(admin.ModelAdmin):
    list_display = ('order', 'stage_type', 'get_workshop', 'finished_good', 'in_progress', 'completed', 'defective', 'date')
    list_filter = ('stage_type', 'workshop', 'finished_good', 'order')
    search_fields = ('order__name', 'workshop__name')
    readonly_fields = ('date',)

    def get_workshop(self, obj):
        return obj.workshop.__str__() if obj.workshop else ''
    get_workshop.short_description = 'Этап (цех)'

@admin.register(OrderDefect)
class OrderDefectAdmin(admin.ModelAdmin):
    list_display = ('order', 'get_workshop', 'quantity', 'status', 'date', 'rework_deadline', 'rework_cost')
    list_filter = ('status', 'workshop', 'order', 'date')
    search_fields = ('order__name', 'workshop__name', 'comment', 'admin_comment')
    readonly_fields = ('date', 'rework_cost', 'rework_task')
    fieldsets = (
        ('Основная информация', {
            'fields': ('order', 'workshop', 'quantity', 'date', 'comment')
        }),
        ('Статус и управление', {
            'fields': ('status', 'admin_comment', 'rework_deadline')
        }),
        ('Переработка', {
            'fields': ('rework_task', 'rework_cost'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['approve_for_rework', 'reject_defect']

    def get_workshop(self, obj):
        return obj.workshop.__str__() if obj.workshop else ''
    get_workshop.short_description = 'Этап (цех)'
    
    def approve_for_rework(self, request, queryset):
        """Разрешить переработку выбранных браков"""
        count = 0
        for defect in queryset.filter(status='pending_review'):
            success, message = defect.approve_for_rework(
                admin_user=request.user,
                comment='Разрешено через админку'
            )
            if success:
                count += 1
        
        self.message_user(request, f'Разрешена переработка для {count} браков')
    approve_for_rework.short_description = 'Разрешить переработку'
    
    def reject_defect(self, request, queryset):
        """Отклонить выбранные браки"""
        count = 0
        for defect in queryset.filter(status='pending_review'):
            success, message = defect.reject_defect(
                admin_user=request.user,
                comment='Отклонено через админку'
            )
            if success:
                count += 1
        
        self.message_user(request, f'Отклонено {count} браков')
    reject_defect.short_description = 'Отклонить браки'
