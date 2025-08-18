from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from decimal import Decimal
from datetime import date, timedelta

User = get_user_model()

from .models import (
    ExpenseCategory, Supplier, SupplierItem, MainBankAccount, 
    MoneyMovement, Expense, Income, FactoryAsset, FinancialReport
)


class FinanceModelsTestCase(TestCase):
    """Тесты для моделей финансовой системы"""
    
    def setUp(self):
        """Настройка тестовых данных"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        # Создание тестовых данных
        self.category = ExpenseCategory.objects.create(
            name='Тестовая категория',
            description='Описание тестовой категории'
        )
        
        self.supplier = Supplier.objects.create(
            name='Тестовый поставщик',
            contact_person='Тест Тестович',
            phone='+996 555 123 456'
        )
        
        # Получаем основной счет
        self.main_account = MainBankAccount.get_main_account()
    
    def test_main_bank_account_creation(self):
        """Тест создания основного банковского счета"""
        self.assertEqual(self.main_account.currency, 'KGS')
        self.assertEqual(self.main_account.balance, Decimal('0.00'))
        self.assertIsNotNone(self.main_account.description)
    
    def test_main_bank_account_singleton(self):
        """Тест что основной счет создается только один раз"""
        account1 = MainBankAccount.get_main_account()
        account2 = MainBankAccount.get_main_account()
        self.assertEqual(account1.id, account2.id)
        self.assertEqual(account1, account2)
    
    def test_expense_category_creation(self):
        """Тест создания категории расходов"""
        self.assertEqual(self.category.name, 'Тестовая категория')
        self.assertEqual(self.category.description, 'Описание тестовой категории')
        self.assertIsNone(self.category.parent)
    
    def test_supplier_creation(self):
        """Тест создания поставщика"""
        self.assertEqual(self.supplier.name, 'Тестовый поставщик')
        self.assertEqual(self.supplier.contact_person, 'Тест Тестович')
        self.assertEqual(self.supplier.phone, '+996 555 123 456')
    
    def test_money_movement_deposit(self):
        """Тест операции вложения денег"""
        initial_balance = self.main_account.balance
        
        movement = MoneyMovement.objects.create(
            movement_type='deposit',
            amount=Decimal('1000.00'),
            user=self.user,
            comment='Тестовое вложение'
        )
        
        # Проверяем, что баланс обновился
        self.main_account.refresh_from_db()
        self.assertEqual(self.main_account.balance, initial_balance + Decimal('1000.00'))
        
        # Проверяем движение
        self.assertEqual(movement.movement_type, 'deposit')
        self.assertEqual(movement.amount, Decimal('1000.00'))
        self.assertEqual(movement.user, self.user)
    
    def test_money_movement_withdrawal(self):
        """Тест операции инкассации денег"""
        # Сначала пополняем счет
        MoneyMovement.objects.create(
            movement_type='deposit',
            amount=Decimal('2000.00'),
            user=self.user,
            comment='Пополнение для теста'
        )
        
        self.main_account.refresh_from_db()
        initial_balance = self.main_account.balance
        
        movement = MoneyMovement.objects.create(
            movement_type='withdrawal',
            amount=Decimal('500.00'),
            user=self.user,
            comment='Тестовая инкассация'
        )
        
        # Проверяем, что баланс обновился
        self.main_account.refresh_from_db()
        self.assertEqual(self.main_account.balance, initial_balance - Decimal('500.00'))
        
        # Проверяем движение
        self.assertEqual(movement.movement_type, 'withdrawal')
        self.assertEqual(movement.amount, Decimal('500.00'))
    
    def test_expense_creation(self):
        """Тест создания расхода"""
        expense = Expense.objects.create(
            category=self.category,
            amount=Decimal('500.00'),
            description='Тестовый расход',
            supplier=self.supplier,
            date=date.today(),
            created_by=self.user
        )
        
        self.assertEqual(expense.category, self.category)
        self.assertEqual(expense.amount, Decimal('500.00'))
        self.assertEqual(expense.supplier, self.supplier)
        self.assertEqual(expense.created_by, self.user)
    
    def test_income_creation(self):
        """Тест создания дохода"""
        income = Income.objects.create(
            income_type='sales',
            amount=Decimal('1000.00'),
            description='Тестовый доход',
            order_reference='ORDER-001',
            date=date.today(),
            created_by=self.user
        )
        
        self.assertEqual(income.income_type, 'sales')
        self.assertEqual(income.amount, Decimal('1000.00'))
        self.assertEqual(income.order_reference, 'ORDER-001')
    
    def test_factory_asset_creation(self):
        """Тест создания имущества завода"""
        asset = FactoryAsset.objects.create(
            name='Тестовое оборудование',
            asset_type='equipment',
            description='Описание тестового оборудования',
            purchase_price=Decimal('5000.00'),
            current_value=Decimal('4500.00'),
            purchase_date=date.today(),
            location='Тестовый цех',
            supplier=self.supplier
        )
        
        self.assertEqual(asset.name, 'Тестовое оборудование')
        self.assertEqual(asset.asset_type, 'equipment')
        self.assertEqual(asset.purchase_price, Decimal('5000.00'))
        self.assertEqual(asset.current_value, Decimal('4500.00'))
    
    def test_financial_report_calculation(self):
        """Тест расчета финансового отчета"""
        # Создаем тестовые доходы и расходы
        Income.objects.create(
            income_type='sales',
            amount=Decimal('2000.00'),
            description='Тестовый доход 1',
            date=date.today(),
            created_by=self.user
        )
        
        Income.objects.create(
            income_type='other',
            amount=Decimal('500.00'),
            description='Тестовый доход 2',
            date=date.today(),
            created_by=self.user
        )
        
        Expense.objects.create(
            category=self.category,
            amount=Decimal('800.00'),
            description='Тестовый расход 1',
            date=date.today(),
            created_by=self.user
        )
        
        # Создаем отчет
        report = FinancialReport.objects.create(
            report_type='monthly',
            title='Тестовый отчет',
            start_date=date.today(),
            end_date=date.today(),
            created_by=self.user
        )
        
        # Рассчитываем показатели
        report.calculate_totals()
        
        # Проверяем расчеты
        self.assertEqual(report.total_income, Decimal('2500.00'))
        self.assertEqual(report.total_expenses, Decimal('800.00'))
        self.assertEqual(report.net_income, Decimal('1700.00'))
        self.assertEqual(report.operating_income, Decimal('1200.00'))  # 2000 - 800


class FinanceViewsTestCase(TestCase):
    """Тесты для представлений финансовой системы"""
    
    def setUp(self):
        """Настройка тестовых данных"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        # Создание тестовых данных
        self.category = ExpenseCategory.objects.create(
            name='Тестовая категория'
        )
        
        self.supplier = Supplier.objects.create(
            name='Тестовый поставщик'
        )
        
        # Получаем основной счет
        self.main_account = MainBankAccount.get_main_account()
    
    def test_dashboard_view_authenticated(self):
        """Тест доступа к дашборду для авторизованного пользователя"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('finance:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'finance/dashboard.html')
    
    def test_dashboard_view_unauthenticated(self):
        """Тест доступа к дашборду для неавторизованного пользователя"""
        response = self.client.get(reverse('finance:dashboard'))
        self.assertEqual(response.status_code, 302)  # Редирект на страницу входа
    
    def test_expenses_view_authenticated(self):
        """Тест доступа к списку расходов для авторизованного пользователя"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('finance:expenses'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'finance/expenses.html')
    
    def test_expense_create_view_authenticated(self):
        """Тест доступа к созданию расхода для авторизованного пользователя"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('finance:expense_create'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'finance/expense_form.html')
    
    def test_expense_create_post(self):
        """Тест создания расхода через POST запрос"""
        self.client.login(username='testuser', password='testpass123')
        
        data = {
            'category': self.category.id,
            'amount': '500.00',
            'description': 'Тестовый расход',
            'supplier': self.supplier.id,
            'date': date.today().strftime('%Y-%m-%d'),
            'invoice_number': 'INV-001',
            'payment_method': 'Банковский перевод'
        }
        
        response = self.client.post(reverse('finance:expense_create'), data)
        self.assertEqual(response.status_code, 302)  # Редирект после успешного создания
        
        # Проверяем, что расход создался
        expense = Expense.objects.filter(description='Тестовый расход').first()
        self.assertIsNotNone(expense)
        self.assertEqual(expense.amount, Decimal('500.00'))
        self.assertEqual(expense.created_by, self.user)
    
    def test_money_movements_view_authenticated(self):
        """Тест доступа к движению денег для авторизованного пользователя"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('finance:money_movements'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'finance/money_movements.html')
    
    def test_money_movement_create_view_authenticated(self):
        """Тест доступа к созданию движения денег для авторизованного пользователя"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('finance:money_movement_create'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'finance/money_movement_form.html')
    
    def test_money_movement_create_post(self):
        """Тест создания движения денег через POST запрос"""
        self.client.login(username='testuser', password='testpass123')
        
        initial_balance = self.main_account.balance
        
        data = {
            'movement_type': 'deposit',
            'amount': '1000.00',
            'comment': 'Тестовое вложение'
        }
        
        response = self.client.post(reverse('finance:money_movement_create'), data)
        self.assertEqual(response.status_code, 302)  # Редирект после успешного создания
        
        # Проверяем, что движение создалось
        movement = MoneyMovement.objects.filter(comment='Тестовое вложение').first()
        self.assertIsNotNone(movement)
        self.assertEqual(movement.amount, Decimal('1000.00'))
        self.assertEqual(movement.user, self.user)
        
        # Проверяем, что баланс обновился
        self.main_account.refresh_from_db()
        self.assertEqual(self.main_account.balance, initial_balance + Decimal('1000.00'))


class FinanceAPITestCase(TestCase):
    """Тесты для API финансовой системы"""
    
    def setUp(self):
        """Настройка тестовых данных"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        # Создание тестовых данных
        self.category = ExpenseCategory.objects.create(
            name='Тестовая категория'
        )
        
        self.supplier = Supplier.objects.create(
            name='Тестовый поставщик'
        )
    
    def test_get_expense_categories_api(self):
        """Тест API получения категорий расходов"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('finance:api_expense_categories'))
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], 'Тестовая категория')
    
    def test_get_suppliers_api(self):
        """Тест API получения поставщиков"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('finance:api_suppliers'))
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], 'Тестовый поставщик')
    
    def test_dashboard_stats_api(self):
        """Тест API получения статистики дашборда"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('finance:api_dashboard_stats'))
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIsInstance(data, dict)
        self.assertIn('total_balance', data)
        self.assertIn('monthly_income', data)
        self.assertIn('monthly_expenses', data)
        self.assertIn('monthly_profit', data)
        self.assertIn('total_assets', data)


class FinanceFormsTestCase(TestCase):
    """Тесты для форм финансовой системы"""
    
    def setUp(self):
        """Настройка тестовых данных"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        self.category = ExpenseCategory.objects.create(
            name='Тестовая категория'
        )
        
        self.supplier = Supplier.objects.create(
            name='Тестовый поставщик'
        )
    
    def test_expense_form_valid(self):
        """Тест валидной формы расхода"""
        from .forms import ExpenseForm
        
        data = {
            'category': self.category.id,
            'amount': '500.00',
            'description': 'Тестовый расход',
            'supplier': self.supplier.id,
            'date': date.today().strftime('%Y-%m-%d'),
            'invoice_number': 'INV-001',
            'payment_method': 'Банковский перевод'
        }
        
        form = ExpenseForm(data=data)
        self.assertTrue(form.is_valid())
    
    def test_expense_form_invalid(self):
        """Тест невалидной формы расхода"""
        from .forms import ExpenseForm
        
        data = {
            'category': self.category.id,
            'amount': '-100.00',  # Отрицательная сумма
            'description': '',     # Пустое описание
            'date': date.today().strftime('%Y-%m-%d')
        }
        
        form = ExpenseForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('amount', form.errors)
        self.assertIn('description', form.errors)
    
    def test_money_movement_form_valid(self):
        """Тест валидной формы движения денег"""
        from .forms import MoneyMovementForm
        
        data = {
            'movement_type': 'deposit',
            'amount': '1000.00',
            'comment': 'Тестовое вложение'
        }
        
        form = MoneyMovementForm(data=data)
        self.assertTrue(form.is_valid())
    
    def test_money_movement_form_invalid(self):
        """Тест невалидной формы движения денег"""
        from .forms import MoneyMovementForm
        
        data = {
            'movement_type': 'deposit',
            'amount': '0.00',  # Нулевая сумма
            'comment': 'Тестовое вложение'
        }
        
        form = MoneyMovementForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('amount', form.errors)
