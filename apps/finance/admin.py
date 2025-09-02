from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum
from .models import (
    ExpenseCategory, Supplier, SupplierItem, MainBankAccount, 
    MoneyMovement, Expense, Income, FactoryAsset, FinancialReport, AccountingAccount, JournalEntry, JournalEntryLine, AnalyticalAccount, StandardOperation, StandardOperationLine, AccountCorrespondence, FinancialPeriod, Request, RequestItem
)

@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent', 'created_at']
    list_filter = ['parent', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['name']

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['name', 'contact_person', 'phone', 'email', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'contact_person', 'phone', 'email', 'inn']
    ordering = ['name']

@admin.register(SupplierItem)
class SupplierItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'supplier', 'unit_price', 'unit', 'purchase_frequency', 'next_purchase_date']
    list_filter = ['supplier', 'purchase_frequency', 'next_purchase_date']
    search_fields = ['name', 'supplier__name']
    ordering = ['supplier', 'name']

@admin.register(MainBankAccount)
class MainBankAccountAdmin(admin.ModelAdmin):
    list_display = ['balance', 'currency', 'updated_at']
    readonly_fields = ['balance', 'currency', 'updated_at']
    
    def has_add_permission(self, request):
        """Запрещаем создание новых счетов"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Запрещаем удаление основного счета"""
        return False

@admin.register(MoneyMovement)
class MoneyMovementAdmin(admin.ModelAdmin):
    list_display = ['movement_type', 'amount', 'user', 'date', 'comment_short']
    list_filter = ['movement_type', 'date', 'user']
    search_fields = ['comment', 'user__username']
    ordering = ['-date']
    
    def comment_short(self, obj):
        return obj.comment[:50] + '...' if len(obj.comment) > 50 else obj.comment
    comment_short.short_description = 'Комментарий'

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ['category', 'amount', 'supplier', 'date', 'created_by', 'invoice_number']
    list_filter = ['category', 'supplier', 'date', 'payment_method', 'created_by']
    search_fields = ['description', 'invoice_number', 'supplier__name', 'category__name']
    ordering = ['-date']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('category', 'supplier', 'created_by')

@admin.register(Income)
class IncomeAdmin(admin.ModelAdmin):
    list_display = ['income_type', 'amount', 'date', 'created_by', 'order_reference']
    list_filter = ['income_type', 'date', 'created_by']
    search_fields = ['description', 'order_reference']
    ordering = ['-date']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('created_by')

@admin.register(FactoryAsset)
class FactoryAssetAdmin(admin.ModelAdmin):
    list_display = ['name', 'asset_type', 'purchase_price', 'current_value', 'location', 'is_active']
    list_filter = ['asset_type', 'is_active', 'purchase_date', 'supplier']
    search_fields = ['name', 'description', 'location', 'supplier__name']
    ordering = ['asset_type', 'name']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('supplier')

@admin.register(FinancialReport)
class FinancialReportAdmin(admin.ModelAdmin):
    list_display = ['title', 'report_type', 'start_date', 'end_date', 'total_income', 'total_expenses', 'net_income', 'total_assets']
    list_filter = ['report_type', 'start_date', 'end_date', 'created_by']
    search_fields = ['title']
    ordering = ['-created_at']
    readonly_fields = ['total_income', 'total_expenses', 'net_income', 'operating_income', 'total_assets']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('created_by')
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not change:  # Только при создании
            obj.calculate_totals()

class AnalyticalAccountInline(admin.TabularInline):
	model = AnalyticalAccount
	extra = 0

@admin.register(AccountingAccount)
class AccountingAccountAdmin(admin.ModelAdmin):
	list_display = ('code', 'name', 'account_type', 'normal_side', 'parent', 'is_active')
	list_filter = ('account_type', 'normal_side', 'is_active')
	search_fields = ('code', 'name')
	inlines = [AnalyticalAccountInline]

class JournalEntryLineInline(admin.TabularInline):
	model = JournalEntryLine
	extra = 0

@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
	list_display = ('date', 'memo', 'created_by', 'posted')
	date_hierarchy = 'date'
	inlines = [JournalEntryLineInline]

@admin.register(JournalEntryLine)
class JournalEntryLineAdmin(admin.ModelAdmin):
	list_display = ('entry', 'account', 'analytical_account', 'debit', 'credit')
	list_select_related = ('entry', 'account', 'analytical_account')
	search_fields = ('entry__memo', 'account__code', 'account__name')

@admin.register(AnalyticalAccount)
class AnalyticalAccountAdmin(admin.ModelAdmin):
	list_display = ('code', 'name', 'parent_account', 'is_active')
	list_filter = ('is_active', 'parent_account__account_type')
	search_fields = ('code', 'name', 'parent_account__code')
	list_select_related = ('parent_account',)

class StandardOperationLineInline(admin.TabularInline):
	model = StandardOperationLine
	extra = 0

@admin.register(StandardOperation)
class StandardOperationAdmin(admin.ModelAdmin):
	list_display = ('name', 'category', 'is_active', 'created_by')
	list_filter = ('category', 'is_active')
	search_fields = ('name', 'description')
	inlines = [StandardOperationLineInline]

@admin.register(AccountCorrespondence)
class AccountCorrespondenceAdmin(admin.ModelAdmin):
	list_display = ('debit_account', 'credit_account', 'description', 'is_valid')
	list_filter = ('is_valid', 'debit_account__account_type', 'credit_account__account_type')
	search_fields = ('debit_account__code', 'credit_account__code', 'description')
	list_select_related = ('debit_account', 'credit_account')

@admin.register(FinancialPeriod)
class FinancialPeriodAdmin(admin.ModelAdmin):
	list_display = ('name', 'period_type', 'start_date', 'end_date', 'is_closed', 'closed_by')
	list_filter = ('period_type', 'is_closed')
	search_fields = ('name',)
	date_hierarchy = 'start_date'

class RequestItemInline(admin.TabularInline):
    model = RequestItem
    extra = 1
    fields = ['product', 'quantity', 'size', 'color', 'price', 'glass_type', 'paint_type', 'paint_color', 'cnc_specs', 'cutting_specs', 'packaging_notes']


@admin.register(Request)
class RequestAdmin(admin.ModelAdmin):
    list_display = ['name', 'client', 'status', 'created_at', 'total_amount']
    list_filter = ['status', 'created_at']
    search_fields = ['name', 'client__name', 'client__company']
    readonly_fields = ['created_at', 'updated_at', 'order']
    inlines = [RequestItemInline]
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'client', 'status', 'comment', 'total_amount')
        }),
        ('Системная информация', {
            'fields': ('created_at', 'updated_at', 'order'),
            'classes': ('collapse',)
        }),
    )


@admin.register(RequestItem)
class RequestItemAdmin(admin.ModelAdmin):
    list_display = ['request', 'product', 'quantity', 'size', 'color', 'price']
    list_filter = ['request__status', 'product__is_glass']
    search_fields = ['request__name', 'product__name']
