from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum, Q, F
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import json
from django.core.paginator import Paginator

from .models import (
    ExpenseCategory, Supplier, SupplierItem, MainBankAccount, 
    MoneyMovement, Expense, Income, FactoryAsset, FinancialReport
)
from .forms import (
    ExpenseCategoryForm, SupplierForm, SupplierItemForm,
    MoneyMovementForm, ExpenseForm, IncomeForm, FactoryAssetForm, FinancialReportForm
)
from .forms import DebtForm, DebtPaymentForm
from .models import Debt, DebtPayment
from .models import AccountingAccount, JournalEntry, JournalEntryLine
from .forms import AccountingAccountForm, JournalEntryForm, JournalEntryLineForm

# Главная страница финансовой системы
@login_required
def finance_dashboard(request):
	"""Главный дашборд финансовой системы"""
	
	# Получаем основной счет
	main_account = MainBankAccount.get_main_account()
	total_balance = main_account.balance
	
	# Доходы и расходы за текущий месяц
	current_month = timezone.now().month
	current_year = timezone.now().year
	
	monthly_income = Income.objects.filter(
		date__month=current_month,
		date__year=current_year
	).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
	
	monthly_expenses = Expense.objects.filter(
		date__month=current_month,
		date__year=current_year
	).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
	
	monthly_profit = monthly_income - monthly_expenses
	
	# Общая стоимость активов
	total_assets = FactoryAsset.objects.filter(is_active=True).aggregate(
		total=Sum('current_value'))['total'] or Decimal('0.00')
	
	# Последние операции с оптимизацией
	recent_movements = MoneyMovement.objects.select_related('user').order_by('-date', '-id')[:5]
	recent_expenses = Expense.objects.select_related('category', 'supplier').order_by('-date', '-id')[:5]
	recent_incomes = Income.objects.select_related('created_by').order_by('-date', '-id')[:5]
	
	# Поставщики с предстоящими покупками (ограничиваем по дате)
	today = timezone.now().date()
	upcoming_purchases = SupplierItem.objects.select_related('supplier').filter(
		next_purchase_date__gte=today
	).order_by('next_purchase_date')[:5]
	
	context = {
		'total_balance': total_balance,
		'monthly_income': monthly_income,
		'monthly_expenses': monthly_expenses,
		'monthly_profit': monthly_profit,
		'total_assets': total_assets,
		'recent_movements': recent_movements,
		'recent_expenses': recent_expenses,
		'recent_incomes': recent_incomes,
		'upcoming_purchases': upcoming_purchases,
		'main_account': main_account,
	}
	
	return render(request, 'finance/dashboard.html', context)

# ==================== КАТЕГОРИИ РАСХОДОВ ====================
@login_required
def expense_categories(request):
	"""Список категорий расходов"""
	categories_qs = ExpenseCategory.objects.all().order_by('name', 'id')
	paginator = Paginator(categories_qs, 25)
	page_obj = paginator.get_page(request.GET.get('page'))
	return render(request, 'finance/expense_categories.html', {
		'categories': page_obj.object_list,
		'page_obj': page_obj,
		'is_paginated': page_obj.paginator.num_pages > 1,
	})

@login_required
def expense_category_create(request):
	"""Создание новой категории расходов"""
	if request.method == 'POST':
		form = ExpenseCategoryForm(request.POST)
		if form.is_valid():
			form.save()
			messages.success(request, 'Категория успешно создана!')
			return redirect('finance:expense_categories')
	else:
		form = ExpenseCategoryForm()
	
	return render(request, 'finance/expense_category_form.html', {'form': form, 'title': 'Новая категория'})

@login_required
def expense_category_edit(request, pk):
	"""Редактирование категории расходов"""
	category = get_object_or_404(ExpenseCategory, pk=pk)
	if request.method == 'POST':
		form = ExpenseCategoryForm(request.POST, instance=category)
		if form.is_valid():
			form.save()
			messages.success(request, 'Категория успешно обновлена!')
			return redirect('finance:expense_categories')
	else:
		form = ExpenseCategoryForm(instance=category)
	
	return render(request, 'finance/expense_category_form.html', {'form': form, 'title': 'Редактирование категории'})

@login_required
def expense_category_delete(request, pk):
	"""Удаление категории расходов"""
	category = get_object_or_404(ExpenseCategory, pk=pk)
	if request.method == 'POST':
		category.delete()
		messages.success(request, 'Категория успешно удалена!')
		return redirect('finance:expense_categories')
	
	return render(request, 'finance/expense_category_confirm_delete.html', {'category': category})

# ==================== ПОСТАВЩИКИ ====================
@login_required
def suppliers(request):
	"""Список поставщиков"""
	suppliers_qs = Supplier.objects.all().order_by('name', 'id')
	paginator = Paginator(suppliers_qs, 25)
	page_obj = paginator.get_page(request.GET.get('page'))
	return render(request, 'finance/suppliers.html', {
		'suppliers': page_obj.object_list,
		'page_obj': page_obj,
		'is_paginated': page_obj.paginator.num_pages > 1,
	})

@login_required
def supplier_create(request):
	"""Создание нового поставщика"""
	if request.method == 'POST':
		form = SupplierForm(request.POST)
		if form.is_valid():
			form.save()
			messages.success(request, 'Поставщик успешно создан!')
			return redirect('finance:suppliers')
	else:
		form = SupplierForm()
	
	return render(request, 'finance/supplier_form.html', {'form': form, 'title': 'Новый поставщик'})

@login_required
def supplier_edit(request, pk):
	"""Редактирование поставщика"""
	supplier = get_object_or_404(Supplier, pk=pk)
	if request.method == 'POST':
		form = SupplierForm(request.POST, instance=supplier)
		if form.is_valid():
			form.save()
			messages.success(request, 'Поставщик успешно обновлен!')
			return redirect('finance:suppliers')
	else:
		form = SupplierForm(instance=supplier)
	
	return render(request, 'finance/supplier_form.html', {'form': form, 'title': 'Редактирование поставщика'})

@login_required
def supplier_detail(request, pk):
	"""Детальная информация о поставщике"""
	supplier = get_object_or_404(Supplier, pk=pk)
	items_qs = SupplierItem.objects.filter(supplier=supplier).order_by('-next_purchase_date', '-id')
	# Статистика по расходам по поставщику
	expenses_qs = Expense.objects.filter(supplier=supplier)
	total_expenses = expenses_qs.aggregate(s=Sum('amount'))['s'] or Decimal('0.00')
	expenses_count = expenses_qs.count()
	avg_expense = expenses_qs.aggregate(s=Sum('amount'))['s'] / expenses_count if expenses_count else Decimal('0.00')
	last_expense_date = expenses_qs.order_by('-date').values_list('date', flat=True).first()
	items_count = items_qs.count()
	recent_expenses = expenses_qs.order_by('-date', '-id')[:10]
	paginator = Paginator(items_qs, 20)
	page_obj = paginator.get_page(request.GET.get('page'))
	return render(request, 'finance/supplier_detail.html', {
		'supplier': supplier, 
		'items': page_obj.object_list,
		'page_obj': page_obj,
		'is_paginated': page_obj.paginator.num_pages > 1,
		'total_expenses': total_expenses,
		'expenses_count': expenses_count,
		'avg_expense': avg_expense,
		'last_expense_date': last_expense_date,
		'items_count': items_count,
		'recent_expenses': recent_expenses,
	})

@login_required
def supplier_delete(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    if request.method == 'POST':
        supplier.delete()
        messages.success(request, 'Поставщик удален')
        return redirect('finance:suppliers')
    return render(request, 'finance/confirm_delete.html', {'object': supplier, 'title': 'Удалить поставщика'})

# ==================== ТОВАРЫ ПОСТАВЩИКОВ ====================
@login_required
def supplier_items(request):
	"""Список товаров поставщиков"""
	items_qs = SupplierItem.objects.select_related('supplier').all().order_by('-next_purchase_date', '-id')
	# Фильтры
	supplier_id = request.GET.get('supplier')
	search = request.GET.get('search')
	price_min = request.GET.get('price_min')
	price_max = request.GET.get('price_max')
	if supplier_id:
		items_qs = items_qs.filter(supplier_id=supplier_id)
	if search:
		items_qs = items_qs.filter(Q(name__icontains=search) | Q(description__icontains=search))
	if price_min:
		try:
			items_qs = items_qs.filter(unit_price__gte=Decimal(price_min))
		except Exception:
			pass
	if price_max:
		try:
			items_qs = items_qs.filter(unit_price__lte=Decimal(price_max))
		except Exception:
			pass
	# Даты для индикации
	today = timezone.now().date()
	week_from_now = today + timedelta(days=7)
	# Статистика по отфильтрованным данным
	upcoming_items = items_qs.filter(next_purchase_date__gt=today, next_purchase_date__lte=week_from_now).count()
	overdue_items = items_qs.filter(next_purchase_date__lt=today).count()
	total_value = items_qs.aggregate(s=Sum('unit_price'))['s'] or Decimal('0.00')
	paginator = Paginator(items_qs, 25)
	page_obj = paginator.get_page(request.GET.get('page'))
	suppliers = Supplier.objects.all().order_by('name')
	return render(request, 'finance/supplier_items.html', {
		'items': page_obj.object_list,
		'page_obj': page_obj,
		'is_paginated': page_obj.paginator.num_pages > 1,
		'suppliers': suppliers,
		'today': today,
		'week_from_now': week_from_now,
		'upcoming_items': upcoming_items,
		'overdue_items': overdue_items,
		'total_value': total_value,
	})

@login_required
def supplier_item_create(request):
	"""Создание нового товара поставщика"""
	if request.method == 'POST':
		form = SupplierItemForm(request.POST)
		if form.is_valid():
			form.save()
			messages.success(request, 'Товар поставщика успешно создан!')
			return redirect('finance:supplier_items')
	else:
		form = SupplierItemForm()
	
	return render(request, 'finance/supplier_item_form.html', {'form': form, 'title': 'Новый товар'})

# ==================== ДВИЖЕНИЕ ДЕНЕГ ====================
@login_required
def money_movements(request):
	"""Список движения денег"""
	movements_qs = MoneyMovement.objects.select_related('user').all().order_by('-date', '-id')
	movement_type = request.GET.get('movement_type')
	date_from = request.GET.get('date_from')
	date_to = request.GET.get('date_to')
	if movement_type in {'deposit', 'withdrawal'}:
		movements_qs = movements_qs.filter(movement_type=movement_type)
	if date_from:
		try:
			parsed_from = datetime.strptime(date_from, '%Y-%m-%d').date()
			movements_qs = movements_qs.filter(date__date__gte=parsed_from)
		except ValueError:
			pass
	if date_to:
		try:
			parsed_to = datetime.strptime(date_to, '%Y-%m-%d').date()
			movements_qs = movements_qs.filter(date__date__lte=parsed_to)
		except ValueError:
			pass
	paginator = Paginator(movements_qs, 25)
	page_obj = paginator.get_page(request.GET.get('page'))
	# Preserve filters in pagination
	query_params = request.GET.copy()
	query_params.pop('page', None)
	query_string = query_params.urlencode()
	main_account = MainBankAccount.get_main_account()
	return render(request, 'finance/money_movements.html', {
		'movements': page_obj.object_list,
		'page_obj': page_obj,
		'is_paginated': page_obj.paginator.num_pages > 1,
		'query_string': query_string,
		'main_account': main_account,
	})

@login_required
def money_movement_create(request):
	"""Создание нового движения денег"""
	if request.method == 'POST':
		form = MoneyMovementForm(request.POST)
		if form.is_valid():
			movement = form.save(commit=False)
			movement.user = request.user
			movement.save()
			messages.success(request, 'Движение денег успешно создано!')
			return redirect('finance:money_movements')
	else:
		form = MoneyMovementForm()
	
	return render(request, 'finance/money_movement_form.html', {'form': form, 'title': 'Новое движение'})

# ==================== РАСХОДЫ ====================
@login_required
def expenses(request):
	"""Список расходов"""
	expenses_qs = Expense.objects.select_related('category', 'supplier', 'created_by').all().order_by('-date', '-id')
	category_id = request.GET.get('category')
	supplier_id = request.GET.get('supplier')
	date_from = request.GET.get('date_from')
	date_to = request.GET.get('date_to')
	if category_id:
		expenses_qs = expenses_qs.filter(category_id=category_id)
	if supplier_id:
		expenses_qs = expenses_qs.filter(supplier_id=supplier_id)
	if date_from:
		try:
			parsed_from = datetime.strptime(date_from, '%Y-%m-%d').date()
			expenses_qs = expenses_qs.filter(date__gte=parsed_from)
		except ValueError:
			pass
	if date_to:
		try:
			parsed_to = datetime.strptime(date_to, '%Y-%m-%d').date()
			expenses_qs = expenses_qs.filter(date__lte=parsed_to)
		except ValueError:
			pass
	paginator = Paginator(expenses_qs, 25)
	page_obj = paginator.get_page(request.GET.get('page'))
	# Preserve filters in pagination
	query_params = request.GET.copy()
	query_params.pop('page', None)
	query_string = query_params.urlencode()
	categories = ExpenseCategory.objects.all()
	suppliers = Supplier.objects.all()
	return render(request, 'finance/expenses.html', {
		'expenses': page_obj.object_list,
		'categories': categories,
		'suppliers': suppliers,
		'page_obj': page_obj,
		'is_paginated': page_obj.paginator.num_pages > 1,
		'query_string': query_string,
	})

@login_required
def expense_create(request):
	"""Создание нового расхода"""
	if request.method == 'POST':
		form = ExpenseForm(request.POST)
		if form.is_valid():
			expense = form.save(commit=False)
			expense.created_by = request.user
			expense.save()
			messages.success(request, 'Расход успешно создан!')
			return redirect('finance:expenses')
	else:
		form = ExpenseForm()
	
	return render(request, 'finance/expense_form.html', {'form': form, 'title': 'Новый расход'})

@login_required
def expense_edit(request, pk):
	"""Редактирование расхода"""
	expense = get_object_or_404(Expense, pk=pk)
	if request.method == 'POST':
		form = ExpenseForm(request.POST, instance=expense)
		if form.is_valid():
			form.save()
			messages.success(request, 'Расход успешно обновлен!')
			return redirect('finance:expenses')
	else:
		form = ExpenseForm(instance=expense)
	
	return render(request, 'finance/expense_form.html', {'form': form, 'title': 'Редактирование расхода'})

# ==================== ДОХОДЫ ====================
@login_required
def incomes(request):
	"""Список доходов"""
	incomes_qs = Income.objects.select_related('created_by').all().order_by('-date', '-id')
	income_type = request.GET.get('income_type')
	date_from = request.GET.get('date_from')
	date_to = request.GET.get('date_to')
	if income_type in {'sales', 'other'}:
		incomes_qs = incomes_qs.filter(income_type=income_type)
	if date_from:
		try:
			parsed_from = datetime.strptime(date_from, '%Y-%m-%d').date()
			incomes_qs = incomes_qs.filter(date__gte=parsed_from)
		except ValueError:
			pass
	if date_to:
		try:
			parsed_to = datetime.strptime(date_to, '%Y-%m-%d').date()
			incomes_qs = incomes_qs.filter(date__lte=parsed_to)
		except ValueError:
			pass
	paginator = Paginator(incomes_qs, 25)
	page_obj = paginator.get_page(request.GET.get('page'))
	# Preserve filters in pagination
	query_params = request.GET.copy()
	query_params.pop('page', None)
	query_string = query_params.urlencode()
	return render(request, 'finance/incomes.html', {'incomes': page_obj.object_list, 'page_obj': page_obj, 'is_paginated': page_obj.paginator.num_pages > 1, 'query_string': query_string})

@login_required
def income_create(request):
	"""Создание нового дохода"""
	if request.method == 'POST':
		form = IncomeForm(request.POST)
		if form.is_valid():
			income = form.save(commit=False)
			income.created_by = request.user
			income.save()
			messages.success(request, 'Доход успешно создан!')
			return redirect('finance:incomes')
	else:
		form = IncomeForm()
	
	return render(request, 'finance/income_form.html', {'form': form, 'title': 'Новый доход'})

# ==================== ИМУЩЕСТВО ЗАВОДА ====================
@login_required
def factory_assets(request):
	"""Список имущества завода"""
	assets_qs = FactoryAsset.objects.select_related('supplier').all().order_by('-current_value', '-id')
	paginator = Paginator(assets_qs, 25)
	page_obj = paginator.get_page(request.GET.get('page'))
	return render(request, 'finance/factory_assets.html', {
		'assets': page_obj.object_list,
		'page_obj': page_obj,
		'is_paginated': page_obj.paginator.num_pages > 1,
	})

@login_required
def factory_asset_create(request):
	"""Создание нового имущества"""
	if request.method == 'POST':
		form = FactoryAssetForm(request.POST)
		if form.is_valid():
			form.save()
			messages.success(request, 'Имущество успешно добавлено!')
			return redirect('finance:factory_assets')
	else:
		form = FactoryAssetForm()
	
	return render(request, 'finance/factory_asset_form.html', {'form': form, 'title': 'Новое имущество'})

@login_required
def factory_asset_detail(request, pk):
	asset = get_object_or_404(FactoryAsset, pk=pk)
	return render(request, 'finance/factory_asset_detail.html', {'asset': asset})

@login_required
def factory_asset_edit(request, pk):
	asset = get_object_or_404(FactoryAsset, pk=pk)
	if request.method == 'POST':
		form = FactoryAssetForm(request.POST, instance=asset)
		if form.is_valid():
			form.save()
			messages.success(request, 'Имущество обновлено')
			return redirect('finance:factory_assets')
	else:
		form = FactoryAssetForm(instance=asset)
	return render(request, 'finance/factory_asset_form.html', {'form': form})

@login_required
def factory_asset_delete(request, pk):
	asset = get_object_or_404(FactoryAsset, pk=pk)
	if request.method == 'POST':
		asset.delete()
		messages.success(request, 'Имущество удалено')
		return redirect('finance:factory_assets')
	return render(request, 'finance/confirm_delete.html', {'object': asset, 'title': 'Удалить имущество'})

# ==================== ФИНАНСОВЫЕ ОТЧЕТЫ ====================
@login_required
def financial_reports(request):
	"""Список финансовых отчетов"""
	reports_qs = FinancialReport.objects.select_related('created_by').all().order_by('-start_date', '-id')
	paginator = Paginator(reports_qs, 25)
	page_obj = paginator.get_page(request.GET.get('page'))
	
	# Сводные показатели
	total_income = Income.objects.aggregate(s=Sum('amount'))['s'] or Decimal('0.00')
	total_expenses = Expense.objects.aggregate(s=Sum('amount'))['s'] or Decimal('0.00')
	net_profit = total_income - total_expenses
	
	context = {
		'reports': page_obj.object_list,
		'page_obj': page_obj,
		'is_paginated': page_obj.paginator.num_pages > 1,
		'total_income': total_income,
		'total_expenses': total_expenses,
		'total_profit': net_profit,
	}
	return render(request, 'finance/financial_reports.html', context)

@login_required
def financial_report_create(request):
	"""Создание нового финансового отчета"""
	if request.method == 'POST':
		form = FinancialReportForm(request.POST)
		if form.is_valid():
			report = form.save(commit=False)
			report.created_by = request.user
			
			# Получаем дополнительные поля из формы
			report.title = request.POST.get('title', '')
			report.start_date = request.POST.get('start_date')
			report.end_date = request.POST.get('end_date')
			
			report.save()
			report.calculate_totals()  # Рассчитываем показатели
			messages.success(request, 'Финансовый отчет успешно создан!')
			return redirect('finance:financial_reports')
	else:
		form = FinancialReportForm()
	
	return render(request, 'finance/financial_report_form.html', {'form': form, 'title': 'Новый отчет'})

@login_required
def financial_report_export_excel(request, pk):
	report = get_object_or_404(FinancialReport, pk=pk)
	report.calculate_totals()
	from django.http import HttpResponse
	# Генерируем HTML-таблицу, совместимую с Excel
	html = []
	html.append('<html><head><meta charset="utf-8"></head><body>')
	html.append(f'<h2>{report.title}</h2>')
	html.append(f'<p>Период: {report.start_date} - {report.end_date}</p>')
	html.append('<table border="1" cellspacing="0" cellpadding="4">')
	html.append('<tr><th>Показатель</th><th>Значение</th></tr>')
	html.append(f'<tr><td>Общий доход</td><td>{report.total_income}</td></tr>')
	html.append(f'<tr><td>Общий расход</td><td>{report.total_expenses}</td></tr>')
	html.append(f'<tr><td>Чистая прибыль</td><td>{report.net_income}</td></tr>')
	html.append(f'<tr><td>Операционный доход</td><td>{report.operating_income}</td></tr>')
	html.append(f'<tr><td>Общие активы</td><td>{report.total_assets}</td></tr>')
	html.append('</table>')
	# Детализация доходов/расходов
	incomes = Income.objects.filter(date__range=[report.start_date, report.end_date]).order_by('-amount')[:500]
	expenses = Expense.objects.filter(date__range=[report.start_date, report.end_date]).order_by('-amount')[:500]
	html.append('<h3>Доходы</h3>')
	html.append('<table border="1" cellspacing="0" cellpadding="4">')
	html.append('<tr><th>Дата</th><th>Тип</th><th>Сумма</th><th>Описание</th></tr>')
	for inc in incomes:
		html.append(f'<tr><td>{inc.date}</td><td>{inc.get_income_type_display()}</td><td>{inc.amount}</td><td>{inc.description}</td></tr>')
	html.append('</table>')
	html.append('<h3>Расходы</h3>')
	html.append('<table border="1" cellspacing="0" cellpadding="4">')
	html.append('<tr><th>Дата</th><th>Категория</th><th>Поставщик</th><th>Сумма</th><th>Описание</th></tr>')
	for exp in expenses:
		cat = exp.category.name if exp.category_id else ''
		supp = exp.supplier.name if exp.supplier_id else ''
		html.append(f'<tr><td>{exp.date}</td><td>{cat}</td><td>{supp}</td><td>{exp.amount}</td><td>{exp.description}</td></tr>')
	html.append('</table>')
	html.append('</body></html>')
	content = ''.join(html)
	response = HttpResponse(content, content_type='application/vnd.ms-excel; charset=utf-8')
	response['Content-Disposition'] = f'attachment; filename="financial_report_{report.pk}.xls"'
	return response

# Уточним детальный отчет: добавим разбивки и топы
@login_required
def financial_report_detail(request, pk):
	report = get_object_or_404(FinancialReport, pk=pk)
	profit_margin_pct = None
	if report.total_income and report.total_income != 0:
		try:
			profit_margin_pct = (report.net_income / report.total_income) * 100
		except Exception:
			profit_margin_pct = None
	# Подробная аналитика
	incomes_qs = Income.objects.filter(date__range=[report.start_date, report.end_date])
	expenses_qs = Expense.objects.filter(date__range=[report.start_date, report.end_date])
	from django.db.models import Count
	income_by_type = list(incomes_qs.values('income_type').annotate(total=Sum('amount'), cnt=Count('id')).order_by('-total'))
	expense_by_category = list(expenses_qs.values('category__name').annotate(total=Sum('amount'), cnt=Count('id')).order_by('-total'))
	top_incomes = incomes_qs.order_by('-amount')[:10]
	top_expenses = expenses_qs.order_by('-amount')[:10]
	# Динамика по дням
	daily_income = list(incomes_qs.values('date').annotate(total=Sum('amount')).order_by('date'))
	daily_expenses = list(expenses_qs.values('date').annotate(total=Sum('amount')).order_by('date'))
	context = {
		'report': report,
		'profit_margin_pct': profit_margin_pct,
		'income_by_type': income_by_type,
		'expense_by_category': expense_by_category,
		'top_incomes': top_incomes,
		'top_expenses': top_expenses,
		'daily_income': daily_income,
		'daily_expenses': daily_expenses,
	}
	return render(request, 'finance/financial_report_detail.html', context)

@login_required
def financial_report_edit(request, pk):
	report = get_object_or_404(FinancialReport, pk=pk)
	if request.method == 'POST':
		form = FinancialReportForm(request.POST, instance=report)
		if form.is_valid():
			report = form.save(commit=False)
			report.title = request.POST.get('title', report.title)
			report.start_date = request.POST.get('start_date') or report.start_date
			report.end_date = request.POST.get('end_date') or report.end_date
			report.save()
			report.calculate_totals()
			messages.success(request, 'Отчет обновлен')
			return redirect('finance:financial_reports')
	else:
		form = FinancialReportForm(instance=report)
	return render(request, 'finance/financial_report_form.html', {'form': form, 'report': report})

@login_required
def financial_report_delete(request, pk):
	report = get_object_or_404(FinancialReport, pk=pk)
	if request.method == 'POST':
		report.delete()
		messages.success(request, 'Отчет удален')
		return redirect('finance:financial_reports')
	return render(request, 'finance/confirm_delete.html', {'object': report, 'title': 'Удалить отчет'})

@login_required
def financial_report_export_csv(request, pk):
	report = get_object_or_404(FinancialReport, pk=pk)
	# Ensure totals are up to date
	report.calculate_totals()
	import csv
	from django.http import HttpResponse
	response = HttpResponse(content_type='text/csv; charset=utf-8')
	response['Content-Disposition'] = f'attachment; filename="financial_report_{report.pk}.csv"'
	writer = csv.writer(response)
	writer.writerow(['Название', report.title])
	writer.writerow(['Период', f"{report.start_date} - {report.end_date}"])
	writer.writerow([])
	writer.writerow(['Показатель', 'Значение'])
	writer.writerow(['Общий доход', report.total_income])
	writer.writerow(['Общий расход', report.total_expenses])
	writer.writerow(['Чистая прибыль', report.net_income])
	writer.writerow(['Операционный доход', report.operating_income])
	writer.writerow(['Общие активы', report.total_assets])
	return response

# ==================== API ДЛЯ AJAX ====================
@login_required
def get_expense_categories(request):
	"""API для получения категорий расходов"""
	categories = ExpenseCategory.objects.all().order_by('name')[:100]  # Ограничиваем количество
	data = [{'id': cat.id, 'name': cat.name} for cat in categories]
	return JsonResponse(data, safe=False)

@login_required
def get_suppliers(request):
	"""API для получения поставщиков"""
	suppliers = Supplier.objects.all().order_by('name')[:100]  # Ограничиваем количество
	data = [{'id': sup.id, 'name': sup.name} for sup in suppliers]
	return JsonResponse(data, safe=False)

# ==================== ДЕТАЛЬНЫЕ ПРОСМОТРЫ ====================
@login_required
def expense_details(request, pk):
	"""Детальная информация о расходе"""
	expense = get_object_or_404(Expense, pk=pk)
	return render(request, 'finance/expense_details.html', {'expense': expense})

@login_required
def income_details(request, pk):
	"""Детальная информация о доходе"""
	income = get_object_or_404(Income, pk=pk)
	return render(request, 'finance/income_details.html', {'income': income})

@login_required
def money_movement_details(request, pk):
	"""Детальная информация об операции"""
	movement = get_object_or_404(MoneyMovement, pk=pk)
	return render(request, 'finance/money_movement_details.html', {'movement': movement})

@login_required
def supplier_item_details(request, pk):
	"""Детальная информация о товаре поставщика"""
	item = get_object_or_404(SupplierItem, pk=pk)
	today = timezone.now().date()
	week_from_now = today + timedelta(days=7)
	return render(request, 'finance/supplier_item_details.html', {
		'item': item,
		'today': today,
		'week_from_now': week_from_now,
	})

@login_required
def supplier_item_edit(request, pk):
	item = get_object_or_404(SupplierItem, pk=pk)
	if request.method == 'POST':
		form = SupplierItemForm(request.POST, instance=item)
		if form.is_valid():
			form.save()
			messages.success(request, 'Товар обновлен')
			return redirect('finance:supplier_items')
	else:
		form = SupplierItemForm(instance=item)
	return render(request, 'finance/supplier_item_form.html', {'form': form, 'title': 'Редактирование товара'})

@login_required
def supplier_item_delete(request, pk):
	item = get_object_or_404(SupplierItem, pk=pk)
	if request.method == 'POST':
		item.delete()
		messages.success(request, 'Товар удален')
		return redirect('finance:supplier_items')
	return render(request, 'finance/confirm_delete.html', {'object': item, 'title': 'Удалить товар'})

@login_required
def dashboard_stats(request):
	"""API для получения статистики дашборда"""
	# Получаем основной счет
	main_account = MainBankAccount.get_main_account()
	total_balance = main_account.balance
	
	# Доходы и расходы за текущий месяц
	current_month = timezone.now().month
	current_year = timezone.now().year
	
	monthly_income = Income.objects.filter(
		date__month=current_month,
		date__year=current_year
	).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
	
	monthly_expenses = Expense.objects.filter(
		date__month=current_month,
		date__year=current_year
	).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
	
	monthly_profit = monthly_income - monthly_expenses
	
	# Общая стоимость активов
	total_assets = FactoryAsset.objects.filter(is_active=True).aggregate(
		total=Sum('current_value'))['total'] or Decimal('0.00')
	
	data = {
		'total_balance': float(total_balance),
		'monthly_income': float(monthly_income),
		'monthly_expenses': float(monthly_expenses),
		'monthly_profit': float(monthly_profit),
		'total_assets': float(total_assets),
	}
	
	return JsonResponse(data)

# ==================== ДОЛГИ ====================
@login_required
def debts(request):
    """Список долгов"""
    debts_qs = Debt.objects.select_related('supplier', 'created_by').all().order_by('-created_at', '-id')
    direction = request.GET.get('direction')
    status = request.GET.get('status')
    if direction in {'payable', 'receivable'}:
        debts_qs = debts_qs.filter(direction=direction)
    if status in {'open', 'partial', 'closed'}:
        if status == 'open':
            debts_qs = debts_qs.filter(amount_paid=Decimal('0.00'))
        elif status == 'partial':
            debts_qs = debts_qs.filter(amount_paid__gt=Decimal('0.00')).exclude(amount_paid__gte=F('original_amount'))
        else:
            debts_qs = debts_qs.filter(amount_paid__gte=F('original_amount'))
    paginator = Paginator(debts_qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'finance/debts.html', {
        'debts': page_obj.object_list,
        'page_obj': page_obj,
        'is_paginated': page_obj.paginator.num_pages > 1,
    })

@login_required
def debt_create(request):
    """Создание нового долга"""
    if request.method == 'POST':
        form = DebtForm(request.POST)
        if form.is_valid():
            debt = form.save(commit=False)
            debt.created_by = request.user
            debt.save()
            messages.success(request, 'Долг успешно создан!')
            return redirect('finance:debts')
    else:
        form = DebtForm()
    return render(request, 'finance/debt_form.html', {'form': form, 'title': 'Новый долг'})

@login_required
def debt_detail(request, pk):
    debt = get_object_or_404(Debt, pk=pk)
    payments = debt.payments.select_related('created_by').all().order_by('-date', '-id')
    payment_form = DebtPaymentForm()
    return render(request, 'finance/debt_detail.html', {'debt': debt, 'payments': payments, 'payment_form': payment_form})

@login_required
def debt_add_payment(request, pk):
    debt = get_object_or_404(Debt, pk=pk)
    if request.method == 'POST':
        form = DebtPaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.debt = debt
            payment.created_by = request.user
            # Валидация: нельзя оплатить больше остатка
            if payment.amount > debt.outstanding_amount:
                messages.error(request, 'Сумма оплаты превышает остаток долга')
            else:
                payment.save()
                messages.success(request, 'Оплата добавлена!')
                return redirect('finance:debt_detail', pk=debt.pk)
    return redirect('finance:debt_detail', pk=debt.pk)

@login_required
def debt_delete(request, pk):
    debt = get_object_or_404(Debt, pk=pk)
    if request.method == 'POST':
        debt.delete()
        messages.success(request, 'Долг удален')
        return redirect('finance:debts')
    return render(request, 'finance/confirm_delete.html', {'object': debt, 'title': 'Удалить долг'})

@login_required
def accounts(request):
	qs = AccountingAccount.objects.select_related('parent').order_by('code')
	return render(request, 'finance/accounts.html', {'accounts': qs})

@login_required
def account_create(request):
	if request.method == 'POST':
		form = AccountingAccountForm(request.POST)
		if form.is_valid():
			form.save()
			messages.success(request, 'Счет создан')
			return redirect('finance:accounts')
	else:
		form = AccountingAccountForm()
	return render(request, 'finance/account_form.html', {'form': form, 'title': 'Новый счет'})

@login_required
def account_edit(request, pk):
	acc = get_object_or_404(AccountingAccount, pk=pk)
	if request.method == 'POST':
		form = AccountingAccountForm(request.POST, instance=acc)
		if form.is_valid():
			form.save()
			messages.success(request, 'Счет обновлен')
			return redirect('finance:accounts')
	else:
		form = AccountingAccountForm(instance=acc)
	return render(request, 'finance/account_form.html', {'form': form, 'title': 'Редактирование счета'})

@login_required
def journal_entries(request):
	entries = JournalEntry.objects.prefetch_related('lines__account').order_by('-date', '-created_at')
	return render(request, 'finance/journal_entries.html', {'entries': entries})

@login_required
def journal_entry_create(request):
	if request.method == 'POST':
		form = JournalEntryForm(request.POST)
		line_form = JournalEntryLineForm(request.POST, prefix='line')
		if form.is_valid() and line_form.is_valid():
			entry = form.save(commit=False)
			entry.created_by = request.user
			entry.save()
			line = line_form.save(commit=False)
			line.entry = entry
			line.save()
			messages.success(request, 'Операция создана')
			return redirect('finance:journal_entries')
	else:
		form = JournalEntryForm()
		line_form = JournalEntryLineForm(prefix='line')
	return render(request, 'finance/journal_entry_form.html', {'form': form, 'line_form': line_form, 'title': 'Новая операция'})

@login_required
def journal_entry_add_line(request, pk):
	entry = get_object_or_404(JournalEntry, pk=pk)
	if request.method == 'POST':
		form = JournalEntryLineForm(request.POST)
		if form.is_valid():
			line = form.save(commit=False)
			line.entry = entry
			line.save()
			messages.success(request, 'Строка добавлена')
			return redirect('finance:journal_entries')
	return redirect('finance:journal_entries')

@login_required
def trial_balance(request):
	# Оборотно-сальдовая ведомость
	date_from = request.GET.get('date_from')
	date_to = request.GET.get('date_to')
	from datetime import datetime as _dt
	df = _dt.strptime(date_from, '%Y-%m-%d').date() if date_from else None
	dt = _dt.strptime(date_to, '%Y-%m-%d').date() if date_to else None
	rows = []
	total_debit = Decimal('0.00')
	total_credit = Decimal('0.00')
	for acc in AccountingAccount.objects.order_by('code'):
		b = acc.get_balance(df, dt)
		rows.append({'account': acc, **b})
		total_debit += b['debit_turnover']
		total_credit += b['credit_turnover']
	return render(request, 'finance/trial_balance.html', {
		'rows': rows,
		'total_debit': total_debit,
		'total_credit': total_credit,
		'date_from': date_from,
		'date_to': date_to,
	})
