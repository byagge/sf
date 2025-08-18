from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from decimal import Decimal
from datetime import date, timedelta

User = get_user_model()

from apps.finance.models import (
    ExpenseCategory, Supplier, SupplierItem, MainBankAccount, 
    MoneyMovement, Expense, Income, FactoryAsset, FinancialReport
)

class Command(BaseCommand):
    help = 'Первоначальная настройка финансовой системы'

    def add_arguments(self, parser):
        parser.add_argument(
            '--demo-data',
            action='store_true',
            help='Создать демонстрационные данные',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Начинаем настройку финансовой системы...')
        )

        with transaction.atomic():
            # Создание основного банковского счета
            self.create_main_bank_account()
            
            # Создание базовых категорий расходов
            self.create_expense_categories()
            
            # Создание базовых поставщиков
            self.create_suppliers()
            
            if options['demo_data']:
                self.create_demo_data()
            
            self.stdout.write(
                self.style.SUCCESS('Финансовая система успешно настроена!')
            )

    def create_main_bank_account(self):
        """Создание основного банковского счета"""
        self.stdout.write('Создание основного банковского счета...')
        
        account = MainBankAccount.get_main_account()
        
        if account.balance == 0:
            # Устанавливаем начальный баланс
            account.balance = Decimal('1000000.00')
            account.description = 'Основной банковский счет предприятия'
            account.save()
            self.stdout.write(f'  ✓ Создан основной счет с балансом: {account.balance} {account.currency}')
        else:
            self.stdout.write(f'  - Основной счет уже существует с балансом: {account.balance} {account.currency}')

    def create_expense_categories(self):
        """Создание базовых категорий расходов"""
        self.stdout.write('Создание категорий расходов...')
        
        categories_data = [
            # Основные категории
            {'name': 'Материальные расходы', 'description': 'Затраты на сырье и материалы'},
            {'name': 'Заработная плата', 'description': 'Выплаты сотрудникам'},
            {'name': 'Амортизация', 'description': 'Износ основных средств'},
            {'name': 'Коммунальные услуги', 'description': 'Электроэнергия, вода, газ'},
            {'name': 'Аренда', 'description': 'Арендные платежи'},
            {'name': 'Транспорт', 'description': 'Транспортные расходы'},
            {'name': 'Маркетинг', 'description': 'Реклама и продвижение'},
            {'name': 'Административные', 'description': 'Общие административные расходы'},
            
            # Подкатегории для материальных расходов
            {'name': 'Сырье', 'parent_name': 'Материальные расходы', 'description': 'Основное сырье для производства'},
            {'name': 'Вспомогательные материалы', 'parent_name': 'Материальные расходы', 'description': 'Дополнительные материалы'},
            {'name': 'Тара и упаковка', 'parent_name': 'Материальные расходы', 'description': 'Упаковочные материалы'},
            
            # Подкатегории для заработной платы
            {'name': 'Основная зарплата', 'parent_name': 'Заработная плата', 'description': 'Основная заработная плата'},
            {'name': 'Премии', 'parent_name': 'Заработная плата', 'description': 'Премиальные выплаты'},
            {'name': 'Социальные отчисления', 'parent_name': 'Заработная плата', 'description': 'Налоги и отчисления'},
            
            # Подкатегории для коммунальных услуг
            {'name': 'Электроэнергия', 'parent_name': 'Коммунальные услуги', 'description': 'Затраты на электроэнергию'},
            {'name': 'Водоснабжение', 'parent_name': 'Коммунальные услуги', 'description': 'Затраты на воду'},
            {'name': 'Отопление', 'parent_name': 'Коммунальные услуги', 'description': 'Затраты на отопление'},
            {'name': 'Газоснабжение', 'parent_name': 'Коммунальные услуги', 'description': 'Затраты на газ'},
        ]
        
        created_categories = {}
        
        for cat_data in categories_data:
            parent = None
            if 'parent_name' in cat_data:
                parent = created_categories.get(cat_data['parent_name'])
            
            category, created = ExpenseCategory.objects.get_or_create(
                name=cat_data['name'],
                defaults={
                    'description': cat_data['description'],
                    'parent': parent
                }
            )
            
            if created:
                self.stdout.write(f'  ✓ Создана категория: {category.name}')
            else:
                self.stdout.write(f'  - Категория уже существует: {category.name}')
            
            created_categories[cat_data['name']] = category

    def create_suppliers(self):
        """Создание базовых поставщиков"""
        self.stdout.write('Создание поставщиков...')
        
        suppliers_data = [
            {
                'name': 'ООО "Стройматериалы"',
                'contact_person': 'Иванов Иван Иванович',
                'phone': '+996 555 123 456',
                'email': 'info@stroymat.kg',
                'address': 'г. Бишкек, ул. Строительная, 123',
                'inn': '123456789012',
                'bank_details': 'Банк: АКБ "Банк", р/с: 12345678901234567890'
            },
            {
                'name': 'ИП "Электротехника"',
                'contact_person': 'Петров Петр Петрович',
                'phone': '+996 555 234 567',
                'email': 'petrov@electro.kg',
                'address': 'г. Бишкек, ул. Электронная, 456',
                'inn': '987654321098',
                'bank_details': 'Банк: АКБ "Финанс", р/с: 09876543210987654321'
            },
            {
                'name': 'ООО "Транспортные услуги"',
                'contact_person': 'Сидоров Сидор Сидорович',
                'phone': '+996 555 345 678',
                'email': 'transport@logistics.kg',
                'address': 'г. Бишкек, ул. Транспортная, 789',
                'inn': '456789123456',
                'bank_details': 'Банк: АКБ "Транс", р/с: 45678912345678912345'
            },
            {
                'name': 'ИП "Офисные принадлежности"',
                'contact_person': 'Козлова Анна Сергеевна',
                'phone': '+996 555 456 789',
                'email': 'office@supplies.kg',
                'address': 'г. Бишкек, ул. Офисная, 321',
                'inn': '789123456789',
                'bank_details': 'Банк: АКБ "Офис", р/с: 78912345678912345678'
            }
        ]
        
        for supplier_data in suppliers_data:
            supplier, created = Supplier.objects.get_or_create(
                name=supplier_data['name'],
                defaults=supplier_data
            )
            
            if created:
                self.stdout.write(f'  ✓ Создан поставщик: {supplier.name}')
            else:
                self.stdout.write(f'  - Поставщик уже существует: {supplier.name}')

    def create_demo_data(self):
        """Создание демонстрационных данных"""
        self.stdout.write('Создание демонстрационных данных...')
        
        # Создание демонстрационного имущества
        self.create_demo_assets()
        
        self.stdout.write('  ✓ Демонстрационные данные созданы')

    def create_demo_assets(self):
        """Создание демонстрационного имущества"""
        assets_data = [
            {
                'name': 'Производственное здание',
                'asset_type': 'building',
                'description': 'Основное производственное здание площадью 2000 кв.м',
                'purchase_price': Decimal('15000000.00'),
                'current_value': Decimal('18000000.00'),
                'purchase_date': date(2020, 1, 15),
                'location': 'г. Бишкек, промзона №1',
                'supplier': Supplier.objects.filter(name__icontains='Стройматериалы').first()
            },
            {
                'name': 'Производственная линия А',
                'asset_type': 'equipment',
                'description': 'Автоматизированная производственная линия',
                'purchase_price': Decimal('5000000.00'),
                'current_value': Decimal('4000000.00'),
                'purchase_date': date(2021, 3, 20),
                'location': 'Цех №1',
                'supplier': Supplier.objects.filter(name__icontains='Электротехника').first()
            },
            {
                'name': 'Грузовой автомобиль',
                'asset_type': 'vehicle',
                'description': 'Грузовой автомобиль для перевозки продукции',
                'purchase_price': Decimal('800000.00'),
                'current_value': Decimal('600000.00'),
                'purchase_date': date(2022, 6, 10),
                'location': 'Автопарк',
                'supplier': Supplier.objects.filter(name__icontains='Транспортные услуги').first()
            },
            {
                'name': 'Офисная мебель',
                'asset_type': 'furniture',
                'description': 'Мебель для офисных помещений',
                'purchase_price': Decimal('300000.00'),
                'current_value': Decimal('250000.00'),
                'purchase_date': date(2021, 8, 5),
                'location': 'Офис',
                'supplier': Supplier.objects.filter(name__icontains='Офисные принадлежности').first()
            }
        ]
        
        for asset_data in assets_data:
            asset, created = FactoryAsset.objects.get_or_create(
                name=asset_data['name'],
                defaults=asset_data
            )
            
            if created:
                self.stdout.write(f'  ✓ Создан актив: {asset.name} - {asset.current_value} сом')
            else:
                self.stdout.write(f'  - Актив уже существует: {asset.name}') 