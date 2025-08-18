from django import forms
from django.forms import ModelForm
from .models import (
    ExpenseCategory, Supplier, SupplierItem, 
    MoneyMovement, Expense, Income, FactoryAsset, FinancialReport
)

class ExpenseCategoryForm(ModelForm):
    class Meta:
        model = ExpenseCategory
        fields = ['name', 'description', 'parent']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Введите название категории'}),
            'description': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Описание категории'}),
            'parent': forms.Select(attrs={'placeholder': 'Выберите родительскую категорию'}),
        }

class SupplierForm(ModelForm):
    class Meta:
        model = Supplier
        fields = ['name', 'code', 'description', 'category', 'contact_person', 'phone', 'email', 'address', 'inn', 'bank_details', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Название организации'}),
            'code': forms.TextInput(attrs={'placeholder': 'Код поставщика'}),
            'description': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Описание поставщика'}),
            'category': forms.Select(attrs={'placeholder': 'Выберите категорию'}),
            'contact_person': forms.TextInput(attrs={'placeholder': 'Контактное лицо'}),
            'phone': forms.TextInput(attrs={'placeholder': '+996 555 123 456'}),
            'email': forms.EmailInput(attrs={'placeholder': 'email@example.com'}),
            'address': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Адрес организации'}),
            'inn': forms.TextInput(attrs={'placeholder': '1234567890'}),
            'bank_details': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Банковские реквизиты'}),
            'is_active': forms.CheckboxInput(),
        }

class SupplierItemForm(ModelForm):
    class Meta:
        model = SupplierItem
        fields = ['supplier', 'name', 'description', 'unit_price', 'unit', 'purchase_frequency', 'warehouse_connection']
        widgets = {
            'supplier': forms.Select(attrs={'placeholder': 'Выберите поставщика'}),
            'name': forms.TextInput(attrs={'placeholder': 'Название товара'}),
            'description': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Описание товара'}),
            'unit_price': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'placeholder': '0.00'}),
            'unit': forms.TextInput(attrs={'placeholder': 'шт, кг, м и т.д.'}),
            'purchase_frequency': forms.NumberInput(attrs={'min': '1', 'placeholder': '30'}),
            'warehouse_connection': forms.TextInput(attrs={'placeholder': 'Связь со складом'}),
        }

class MoneyMovementForm(ModelForm):
    class Meta:
        model = MoneyMovement
        fields = ['movement_type', 'amount', 'comment']
        widgets = {
            'movement_type': forms.Select(attrs={'placeholder': 'Выберите тип операции'}),
            'amount': forms.NumberInput(attrs={'step': '0.01', 'min': '0.01', 'placeholder': '0.00'}),
            'comment': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Комментарий к операции'}),
        }

class ExpenseForm(ModelForm):
    class Meta:
        model = Expense
        fields = ['category', 'amount', 'description', 'supplier', 'date', 'invoice_number', 'payment_method']
        widgets = {
            'category': forms.Select(attrs={'placeholder': 'Выберите категорию'}),
            'amount': forms.NumberInput(attrs={'step': '0.01', 'min': '0.01', 'placeholder': '0.00'}),
            'description': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Описание расхода'}),
            'supplier': forms.Select(attrs={'placeholder': 'Выберите поставщика'}),
            'date': forms.DateInput(attrs={'type': 'date'}),
            'invoice_number': forms.TextInput(attrs={'placeholder': 'Номер счета'}),
            'payment_method': forms.TextInput(attrs={'placeholder': 'Способ оплаты'}),
        }

class IncomeForm(ModelForm):
    class Meta:
        model = Income
        fields = ['income_type', 'amount', 'description', 'order_reference', 'date']
        widgets = {
            'income_type': forms.Select(attrs={'placeholder': 'Выберите тип дохода'}),
            'amount': forms.NumberInput(attrs={'step': '0.01', 'min': '0.01', 'placeholder': '0.00'}),
            'description': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Описание дохода'}),
            'order_reference': forms.TextInput(attrs={'placeholder': 'Номер заказа'}),
            'date': forms.DateInput(attrs={'type': 'date'}),
        }

class FactoryAssetForm(ModelForm):
    class Meta:
        model = FactoryAsset
        fields = ['name', 'asset_type', 'description', 'purchase_price', 'current_value', 'purchase_date', 'location', 'supplier', 'warranty_expiry']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Название актива'}),
            'asset_type': forms.Select(attrs={'placeholder': 'Выберите тип актива'}),
            'description': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Описание актива'}),
            'purchase_price': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'placeholder': '0.00'}),
            'current_value': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'placeholder': '0.00'}),
            'purchase_date': forms.DateInput(attrs={'type': 'date'}),
            'location': forms.TextInput(attrs={'placeholder': 'Местоположение'}),
            'supplier': forms.Select(attrs={'placeholder': 'Выберите поставщика'}),
            'warranty_expiry': forms.DateInput(attrs={'type': 'date'}),
        }

class FinancialReportForm(ModelForm):
    class Meta:
        model = FinancialReport
        fields = ['report_type']
        widgets = {
            'report_type': forms.Select(attrs={'placeholder': 'Выберите тип отчета'}),
        }