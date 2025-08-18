from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from decimal import Decimal
import uuid

User = get_user_model()

# Категории расходов
class ExpenseCategory(models.Model):
    name = models.CharField(max_length=100, verbose_name="Название категории")
    description = models.TextField(blank=True, verbose_name="Описание")
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, verbose_name="Родительская категория")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Категория расходов"
        verbose_name_plural = "Категории расходов"
        ordering = ['name']
    
    def __str__(self):
        return self.name

# Поставщики
class Supplier(models.Model):
    CATEGORY_CHOICES = [
        ('materials', 'Материалы'),
        ('services', 'Услуги'),
        ('equipment', 'Оборудование'),
        ('other', 'Другое'),
    ]
    
    name = models.CharField(max_length=200, verbose_name="Название поставщика")
    code = models.CharField(max_length=50, blank=True, verbose_name="Код поставщика")
    description = models.TextField(blank=True, verbose_name="Описание")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other', verbose_name="Категория")
    contact_person = models.CharField(max_length=100, blank=True, verbose_name="Контактное лицо")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Телефон")
    email = models.EmailField(blank=True, verbose_name="Email")
    address = models.TextField(blank=True, verbose_name="Адрес")
    inn = models.CharField(max_length=12, blank=True, verbose_name="ИНН")
    bank_details = models.TextField(blank=True, verbose_name="Банковские реквизиты")
    is_active = models.BooleanField(default=True, verbose_name="Активный")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Поставщик"
        verbose_name_plural = "Поставщики"
        ordering = ['name']
    
    def __str__(self):
        return self.name

# Товары/услуги поставщиков
class SupplierItem(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, verbose_name="Поставщик")
    name = models.CharField(max_length=200, verbose_name="Название товара/услуги")
    description = models.TextField(blank=True, verbose_name="Описание")
    unit_price = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Цена за единицу (сом)")
    unit = models.CharField(max_length=50, verbose_name="Единица измерения")
    purchase_frequency = models.IntegerField(verbose_name="Частота покупок (дней)", default=30)
    last_purchase_date = models.DateField(null=True, blank=True, verbose_name="Дата последней покупки")
    next_purchase_date = models.DateField(null=True, blank=True, verbose_name="Дата следующей покупки")
    warehouse_connection = models.CharField(max_length=200, blank=True, verbose_name="Связь со складом")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Товар поставщика"
        verbose_name_plural = "Товары поставщиков"
        ordering = ['supplier', 'name']
    
    def __str__(self):
        return f"{self.supplier.name} - {self.name}"

# Основной банковский счет (единственный)
class MainBankAccount(models.Model):
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Баланс (сом)")
    currency = models.CharField(max_length=3, default="KGS", verbose_name="Валюта")
    description = models.TextField(blank=True, verbose_name="Описание")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    
    class Meta:
        verbose_name = "Основной банковский счет"
        verbose_name_plural = "Основной банковский счет"
    
    def __str__(self):
        return f"Основной счет - {self.balance} {self.currency}"
    
    @classmethod
    def get_main_account(cls):
        """Получить основной счет, создав его если не существует"""
        account, created = cls.objects.get_or_create(
            id=1,
            defaults={
                'balance': Decimal('0.00'),
                'currency': 'KGS',
                'description': 'Основной банковский счет предприятия'
            }
        )
        return account

# Движение денег
class MoneyMovement(models.Model):
    MOVEMENT_TYPES = [
        ('deposit', 'Вложение'),
        ('withdrawal', 'Инкассация'),
    ]
    
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPES, verbose_name="Тип движения")
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Сумма (сом)")
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    comment = models.TextField(blank=True, verbose_name="Комментарий")
    date = models.DateTimeField(auto_now_add=True, verbose_name="Дата")
    
    class Meta:
        verbose_name = "Движение денег"
        verbose_name_plural = "Движение денег"
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.get_movement_type_display()} - {self.amount} сом - {self.date.strftime('%d.%m.%Y')}"
    
    def save(self, *args, **kwargs):
        if not self.pk:  # Только при создании
            account = MainBankAccount.get_main_account()
            if self.movement_type == 'deposit':
                account.balance += self.amount
            else:
                account.balance -= self.amount
            account.save()
        super().save(*args, **kwargs)

# Расходы
class Expense(models.Model):
    category = models.ForeignKey(ExpenseCategory, on_delete=models.CASCADE, verbose_name="Категория")
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Сумма (сом)")
    description = models.TextField(verbose_name="Описание")
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Поставщик")
    date = models.DateField(verbose_name="Дата расхода")
    invoice_number = models.CharField(max_length=100, blank=True, verbose_name="Номер счета")
    payment_method = models.CharField(max_length=50, blank=True, verbose_name="Способ оплаты")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Создал")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Расход"
        verbose_name_plural = "Расходы"
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.category.name} - {self.amount} сом - {self.date}"
    
    def save(self, *args, **kwargs):
        if not self.pk:  # Только при создании
            account = MainBankAccount.get_main_account()
            account.balance -= self.amount  # Расход уменьшает баланс
            account.save()
        super().save(*args, **kwargs)

# Доходы
class Income(models.Model):
    INCOME_TYPES = [
        ('sales', 'С продаж'),
        ('other', 'Другое'),
    ]
    
    income_type = models.CharField(max_length=20, choices=INCOME_TYPES, verbose_name="Тип дохода")
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Сумма (сом)")
    description = models.TextField(verbose_name="Описание")
    order_reference = models.CharField(max_length=100, blank=True, verbose_name="Ссылка на заказ")
    date = models.DateField(verbose_name="Дата дохода")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Создал")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Доход"
        verbose_name_plural = "Доходы"
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.get_income_type_display()} - {self.amount} сом - {self.date}"
    
    def save(self, *args, **kwargs):
        if not self.pk:  # Только при создании
            account = MainBankAccount.get_main_account()
            account.balance += self.amount  # Доход увеличивает баланс
            account.save()
        super().save(*args, **kwargs)

# Состояние имущества завода
class FactoryAsset(models.Model):
    ASSET_TYPES = [
        ('building', 'Здание'),
        ('equipment', 'Оборудование'),
        ('vehicle', 'Транспорт'),
        ('furniture', 'Мебель'),
        ('electronics', 'Электроника'),
        ('other', 'Другое'),
    ]
    
    name = models.CharField(max_length=200, verbose_name="Название")
    asset_type = models.CharField(max_length=20, choices=ASSET_TYPES, verbose_name="Тип имущества")
    description = models.TextField(blank=True, verbose_name="Описание")
    purchase_price = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Цена покупки (сом)")
    current_value = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Текущая стоимость (сом)")
    purchase_date = models.DateField(verbose_name="Дата покупки")
    location = models.CharField(max_length=200, blank=True, verbose_name="Местоположение")
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Поставщик")
    warranty_expiry = models.DateField(null=True, blank=True, verbose_name="Дата окончания гарантии")
    is_active = models.BooleanField(default=True, verbose_name="Активно")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Имущество завода"
        verbose_name_plural = "Имущество завода"
        ordering = ['asset_type', 'name']
    
    def __str__(self):
        return f"{self.name} - {self.current_value} сом"

# Финансовые отчеты
class FinancialReport(models.Model):
    REPORT_TYPES = [
        ('monthly', 'Месячный'),
        ('quarterly', 'Квартальный'),
        ('yearly', 'Годовой'),
        ('custom', 'Произвольный'),
    ]
    
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES, verbose_name="Тип отчета")
    title = models.CharField(max_length=200, verbose_name="Название отчета")
    start_date = models.DateField(verbose_name="Дата начала")
    end_date = models.DateField(verbose_name="Дата окончания")
    total_income = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Общий доход")
    total_expenses = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Общий расход")
    net_income = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Чистый доход")
    operating_income = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Операционный доход")
    total_assets = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Общая стоимость активов")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Создал")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Финансовый отчет"
        verbose_name_plural = "Финансовые отчеты"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} ({self.start_date} - {self.end_date})"
    
    def calculate_totals(self):
        """Расчет всех показателей отчета"""
        # Доходы за период
        incomes = Income.objects.filter(date__range=[self.start_date, self.end_date])
        self.total_income = sum(income.amount for income in incomes)
        
        # Расходы за период
        expenses = Expense.objects.filter(date__range=[self.start_date, self.end_date])
        self.total_expenses = sum(expense.amount for expense in expenses)
        
        # Чистый доход
        self.net_income = self.total_income - self.total_expenses
        
        # Операционный доход (доходы от продаж минус расходы)
        sales_income = sum(income.amount for income in incomes if income.income_type == 'sales')
        self.operating_income = sales_income - self.total_expenses
        
        # Общая стоимость активов
        assets = FactoryAsset.objects.filter(is_active=True)
        self.total_assets = sum(asset.current_value for asset in assets)
        
        self.save()
