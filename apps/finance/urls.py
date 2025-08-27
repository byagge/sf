from django.urls import path
from . import views

app_name = 'finance'

urlpatterns = [
    # Главная страница
    path('', views.finance_dashboard, name='dashboard'),
    
    # Категории расходов
    path('expense-categories/', views.expense_categories, name='expense_categories'),
    path('expense-categories/create/', views.expense_category_create, name='expense_category_create'),
    path('expense-categories/<int:pk>/edit/', views.expense_category_edit, name='expense_category_edit'),
    path('expense-categories/<int:pk>/delete/', views.expense_category_delete, name='expense_category_delete'),
    
    # Поставщики
    path('suppliers/', views.suppliers, name='suppliers'),
    path('suppliers/create/', views.supplier_create, name='supplier_create'),
    path('suppliers/<int:pk>/edit/', views.supplier_edit, name='supplier_edit'),
    path('suppliers/<int:pk>/delete/', views.supplier_delete, name='supplier_delete'),
    path('suppliers/<int:pk>/', views.supplier_detail, name='supplier_detail'),
    
    # Товары поставщиков
    path('supplier-items/', views.supplier_items, name='supplier_items'),
    path('supplier-items/create/', views.supplier_item_create, name='supplier_item_create'),
    path('supplier-items/<int:pk>/details/', views.supplier_item_details, name='supplier_item_details'),
    path('supplier-items/<int:pk>/edit/', views.supplier_item_edit, name='supplier_item_edit'),
    path('supplier-items/<int:pk>/delete/', views.supplier_item_delete, name='supplier_item_delete'),
    
    # Движение денег
    path('money-movements/', views.money_movements, name='money_movements'),
    path('money-movements/create/', views.money_movement_create, name='money_movement_create'),
    path('money-movements/<int:pk>/details/', views.money_movement_details, name='money_movement_details'),
    
    # Расходы
    path('expenses/', views.expenses, name='expenses'),
    path('expenses/create/', views.expense_create, name='expense_create'),
    path('expenses/<int:pk>/edit/', views.expense_edit, name='expense_edit'),
    path('expenses/<int:pk>/details/', views.expense_details, name='expense_details'),
    
    # Доходы
    path('incomes/', views.incomes, name='incomes'),
    path('incomes/create/', views.income_create, name='income_create'),
    path('incomes/<int:pk>/details/', views.income_details, name='income_details'),
    
    # Имущество завода
    path('factory-assets/', views.factory_assets, name='factory_assets'),
    path('factory-assets/create/', views.factory_asset_create, name='factory_asset_create'),
    path('factory-assets/<int:pk>/', views.factory_asset_detail, name='factory_asset_detail'),
    path('factory-assets/<int:pk>/edit/', views.factory_asset_edit, name='factory_asset_edit'),
    path('factory-assets/<int:pk>/delete/', views.factory_asset_delete, name='factory_asset_delete'),
    
    # Финансовые отчеты
    path('financial-reports/', views.financial_reports, name='financial_reports'),
    path('financial-reports/create/', views.financial_report_create, name='financial_report_create'),
    path('financial-reports/<int:pk>/', views.financial_report_detail, name='financial_report_detail'),
    path('financial-reports/<int:pk>/edit/', views.financial_report_edit, name='financial_report_edit'),
    path('financial-reports/<int:pk>/delete/', views.financial_report_delete, name='financial_report_delete'),
    path('financial-reports/<int:pk>/export/csv/', views.financial_report_export_csv, name='financial_report_export_csv'),
    path('financial-reports/<int:pk>/export/excel/', views.financial_report_export_excel, name='financial_report_export_excel'),
    
    # API для AJAX
    path('api/expense-categories/', views.get_expense_categories, name='api_expense_categories'),
    path('api/suppliers/', views.get_suppliers, name='api_suppliers'),
    path('api/dashboard-stats/', views.dashboard_stats, name='api_dashboard_stats'),

    # Долги
    path('debts/', views.debts, name='debts'),
    path('debts/create/', views.debt_create, name='debt_create'),
    path('debts/<int:pk>/', views.debt_detail, name='debt_detail'),
    path('debts/<int:pk>/add-payment/', views.debt_add_payment, name='debt_add_payment'),
    path('debts/<int:pk>/delete/', views.debt_delete, name='debt_delete'),

    # Бухгалтерия (двойная запись)
    path('accounts/', views.accounts, name='accounts'),
    path('accounts/create/', views.account_create, name='account_create'),
    path('accounts/<int:pk>/edit/', views.account_edit, name='account_edit'),
    path('journal/', views.journal_entries, name='journal_entries'),
    path('journal/create/', views.journal_entry_create, name='journal_entry_create'),
    path('journal/<uuid:pk>/add-line/', views.journal_entry_add_line, name='journal_entry_add_line'),
    path('trial-balance/', views.trial_balance, name='trial_balance'),
]
