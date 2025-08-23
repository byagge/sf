from django.contrib import admin
from .models import Order, OrderStage, OrderDefect, OrderItem

class OrderStageInline(admin.TabularInline):
    model = OrderStage
    extra = 1
    fields = ('stage_type', 'workshop', 'order_item', 'parallel_group', 'operation', 'sequence', 'plan_quantity', 'completed_quantity', 'status', 'deadline')
    readonly_fields = ('date',)

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1
    fields = ('product', 'quantity', 'size', 'color', 'glass_type', 'paint_type', 'paint_color')
    
    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        # Динамически обновляем поля в зависимости от выбранного продукта
        return formset

class OrderDefectInline(admin.TabularInline):
    model = OrderDefect
    extra = 0
    fields = ('workshop', 'quantity', 'date', 'comment')
    readonly_fields = ('date',)

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'client', 'get_workshop', 'get_items_count', 'get_total_quantity', 'status', 'has_glass_items', 'expenses', 'created_at')
    list_filter = ('status', 'workshop', 'client', 'created_at')
    search_fields = ('name', 'client__name', 'comment', 'workshop__name')
    readonly_fields = ('expenses', 'created_at', 'has_glass_items', 'glass_items', 'regular_items')
    inlines = [OrderItemInline, OrderStageInline, OrderDefectInline]
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'client', 'workshop', 'status', 'comment')
        }),
        ('Продукты', {
            'fields': ('product', 'quantity'),
            'description': 'Для одиночных продуктов (устаревший способ)',
            'classes': ('collapse',)
        }),
        ('Статистика', {
            'fields': ('has_glass_items', 'glass_items', 'regular_items', 'expenses'),
            'classes': ('collapse',)
        }),
    )

    def get_workshop(self, obj):
        return obj.workshop.__str__() if obj.workshop else ''
    get_workshop.short_description = 'Этап (цех)'

    def get_total_quantity(self, obj):
        return obj.total_quantity
    get_total_quantity.short_description = 'Итого шт.'
    
    def get_items_count(self, obj):
        return obj.items.count()
    get_items_count.short_description = 'Позиций'
    
    def has_glass_items(self, obj):
        return obj.has_glass_items
    has_glass_items.boolean = True
    has_glass_items.short_description = 'Есть стекло'
    
    def glass_items(self, obj):
        items = obj.glass_items
        if not items:
            return "Нет стеклянных изделий"
        return ", ".join([f"{item['product']} x{item['quantity']}" for item in items])
    glass_items.short_description = 'Стеклянные изделия'
    
    def regular_items(self, obj):
        items = obj.regular_items
        if not items:
            return "Нет обычных изделий"
        return ", ".join([f"{item['product']} x{item['quantity']}" for item in items])
    regular_items.short_description = 'Обычные изделия'

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'quantity', 'size', 'color', 'is_glass', 'glass_type', 'paint_type', 'paint_color')
    list_filter = ('product__is_glass', 'glass_type', 'paint_type', 'order__status')
    search_fields = ('order__name', 'product__name', 'size', 'color')
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('order', 'product', 'quantity')
        }),
        ('Характеристики', {
            'fields': ('size', 'color')
        }),
        ('Стеклянные изделия', {
            'fields': ('glass_type',),
            'classes': ('collapse',),
            'description': 'Настройки для стеклянных изделий'
        }),
        ('Покраска', {
            'fields': ('paint_type', 'paint_color'),
            'classes': ('collapse',)
        }),
        ('Спецификации', {
            'fields': ('cnc_specs', 'cutting_specs', 'packaging_notes'),
            'classes': ('collapse',)
        }),
        ('Прогресс', {
            'fields': ('glass_cutting_completed', 'glass_cutting_quantity', 'packaging_received_quantity'),
            'classes': ('collapse',),
            'description': 'Отслеживание прогресса по цехам'
        }),
    )
    
    readonly_fields = ('glass_cutting_completed', 'glass_cutting_quantity', 'packaging_received_quantity')
    
    def is_glass(self, obj):
        return obj.product.is_glass if obj.product else False
    is_glass.boolean = True
    is_glass.short_description = 'Стекло'

@admin.register(OrderStage)
class OrderStageAdmin(admin.ModelAdmin):
    list_display = ('order', 'order_item', 'stage_type', 'get_workshop', 'operation', 'sequence', 'parallel_group', 'plan_quantity', 'completed_quantity', 'status', 'deadline')
    list_filter = ('stage_type', 'workshop', 'status', 'parallel_group', 'order__status')
    search_fields = ('order__name', 'workshop__name', 'operation')
    readonly_fields = ('date',)
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('order', 'order_item', 'stage_type', 'workshop', 'operation')
        }),
        ('Параметры этапа', {
            'fields': ('sequence', 'parallel_group', 'plan_quantity', 'completed_quantity', 'deadline')
        }),
        ('Статус', {
            'fields': ('status', 'in_progress', 'completed', 'defective', 'comment')
        }),
        ('Дополнительно', {
            'fields': ('finished_good', 'date'),
            'classes': ('collapse',)
        }),
    )

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