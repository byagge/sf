from django.shortcuts import render
from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q, Count, Sum, Avg
from django.utils import timezone
from datetime import timedelta
from .models import Workshop
from .serializers import WorkshopSerializer

# Create your views here.

class WorkshopViewSet(viewsets.ModelViewSet):
	queryset = Workshop.objects.all().order_by('name', 'id')
	serializer_class = WorkshopSerializer
	permission_classes = [permissions.IsAuthenticated]
	filter_backends = [filters.SearchFilter, filters.OrderingFilter]
	search_fields = ['name', 'description']
	ordering_fields = ['name', 'created_at']

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def master_workshops(request):
	"""
	Получает все цеха, которыми управляет текущий мастер
	"""
	if request.user.role != 'master':
		return Response({'error': 'Доступ только для мастеров'}, status=403)
	
	# Получаем цеха, где пользователь является главным мастером
	managed_workshops = Workshop.objects.filter(
		manager=request.user,
		is_active=True
	).prefetch_related('users')
	
	# Получаем цеха, где пользователь является дополнительным мастером
	additional_workshops = Workshop.objects.filter(
		workshop_masters__master=request.user,
		workshop_masters__is_active=True,
		is_active=True
	).prefetch_related('users')
	
	# Объединяем все цеха
	all_workshops = list(managed_workshops) + list(additional_workshops)
	
	workshops_data = []
	for workshop in all_workshops:
		# Подсчитываем сотрудников
		employees_count = workshop.users.count()
		
		# Подсчитываем активные задачи
		from apps.employee_tasks.models import EmployeeTask
		active_tasks = EmployeeTask.objects.filter(
			stage__workshop=workshop,
			is_completed=False
		).count()
		
		# Подсчитываем активные заказы
		from apps.orders.models import OrderStage
		active_orders = OrderStage.objects.filter(
			workshop=workshop,
			status='in_progress'
		).count()
		
		workshops_data.append({
			'id': workshop.id,
			'name': workshop.name,
			'description': workshop.description,
			'employees_count': employees_count,
			'active_tasks': active_tasks,
			'active_orders': active_orders,
			'is_main_manager': workshop.manager == request.user
		})
	
	return Response(workshops_data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def master_overview(request):
	"""
	Получает общую статистику по всем цехам мастера
	"""
	if request.user.role != 'master':
		return Response({'error': 'Доступ только для мастеров'}, status=403)
	
	# Получаем все цеха мастера
	managed_workshops = Workshop.objects.filter(
		Q(manager=request.user) | Q(workshop_masters__master=request.user, workshop_masters__is_active=True),
		is_active=True
	)
	
	workshop_ids = list(managed_workshops.values_list('id', flat=True))
	
	# Импортируем необходимые модели
	from apps.employee_tasks.models import EmployeeTask
	from apps.orders.models import OrderStage
	from apps.defects.models import Defect
	from apps.employees.models import EmployeeStatistics
	
	# Общая статистика
	total_employees = sum(workshop.users.count() for workshop in managed_workshops)
	total_active_tasks = EmployeeTask.objects.filter(
		stage__workshop_id__in=workshop_ids,
		is_completed=False
	).count()
	
	total_active_orders = OrderStage.objects.filter(
		workshop_id__in=workshop_ids,
		status='in_progress'
	).count()
	
	# Статистика за последние 30 дней
	thirty_days_ago = timezone.now() - timedelta(days=30)
	
	completed_tasks = EmployeeTask.objects.filter(
		stage__workshop_id__in=workshop_ids,
		is_completed=True,
		completed_at__gte=thirty_days_ago
	)
	
	total_completed_quantity = completed_tasks.aggregate(
		total=Sum('completed_quantity')
	)['total'] or 0
	
	total_defective_quantity = completed_tasks.aggregate(
		total=Sum('defective_quantity')
	)['total'] or 0
	
	# Производительность (задач в день)
	tasks_per_day = total_active_tasks / 30 if total_active_tasks > 0 else 0
	
	overview = {
		'total_workshops': len(workshop_ids),
		'total_employees': total_employees,
		'total_active_tasks': total_active_tasks,
		'total_active_orders': total_active_orders,
		'products_made_30_days': total_completed_quantity,
		'defective_products_30_days': total_defective_quantity,
		'tasks_per_day': round(tasks_per_day, 1),
		'quality_rate': round((total_completed_quantity - total_defective_quantity) / total_completed_quantity * 100, 1) if total_completed_quantity > 0 else 100
	}
	
	return Response(overview)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def workshop_detailed_stats(request, workshop_id):
	"""
	Получает детальную статистику по конкретному цеху мастера
	"""
	if request.user.role != 'master':
		return Response({'error': 'Доступ только для мастеров'}, status=403)
	
	try:
		workshop = Workshop.objects.get(
			id=workshop_id,
			is_active=True
		)
		
		# Проверяем, является ли пользователь мастером этого цеха
		if not (workshop.manager == request.user or 
				workshop.workshop_masters.filter(master=request.user, is_active=True).exists()):
			return Response({'error': 'Доступ запрещен'}, status=403)
		
	except Workshop.DoesNotExist:
		return Response({'error': 'Цех не найден'}, status=404)
	
	# Импортируем необходимые модели
	from apps.employee_tasks.models import EmployeeTask
	from apps.orders.models import OrderStage
	from apps.defects.models import Defect
	from apps.employees.models import EmployeeStatistics
	
	# Статистика сотрудников
	employees = workshop.users.all()
	employees_stats = []
	
	for employee in employees:
		# Задачи сотрудника за последние 30 дней
		thirty_days_ago = timezone.now() - timedelta(days=30)
		employee_tasks = EmployeeTask.objects.filter(
			employee=employee,
			stage__workshop=workshop,
			completed_at__gte=thirty_days_ago
		)
		
		completed_quantity = employee_tasks.aggregate(
			total=Sum('completed_quantity')
		)['total'] or 0
		
		defective_quantity = employee_tasks.aggregate(
			total=Sum('defective_quantity')
		)['total'] or 0
		
		earnings = employee_tasks.aggregate(
			total=Sum('earnings')
		)['total'] or 0
		
		employees_stats.append({
			'id': employee.id,
			'name': employee.get_full_name(),
			'completed_quantity': completed_quantity,
			'defective_quantity': defective_quantity,
			'earnings': earnings,
			'quality_rate': round((completed_quantity - defective_quantity) / completed_quantity * 100, 1) if completed_quantity > 0 else 100
		})
	
	# Статистика заказов
	active_orders = OrderStage.objects.filter(
		workshop=workshop,
		status='in_progress'
	).select_related('order', 'product')
	
	orders_stats = []
	for order_stage in active_orders:
		# Задачи по этому этапу
		tasks = EmployeeTask.objects.filter(stage=order_stage)
		total_quantity = order_stage.plan_quantity
		completed_quantity = tasks.aggregate(
			total=Sum('completed_quantity')
		)['total'] or 0
		
		orders_stats.append({
			'id': order_stage.id,
			'order_name': order_stage.order.name,
			'product_name': order_stage.product.name,
			'operation': order_stage.operation,
			'plan_quantity': total_quantity,
			'completed_quantity': completed_quantity,
			'progress_percent': round(completed_quantity / total_quantity * 100, 1) if total_quantity > 0 else 0,
			'deadline': order_stage.deadline.isoformat() if order_stage.deadline else None
		})
	
	# Общая статистика цеха
	thirty_days_ago = timezone.now() - timedelta(days=30)
	workshop_tasks = EmployeeTask.objects.filter(
		stage__workshop=workshop,
		completed_at__gte=thirty_days_ago
	)
	
	total_completed = workshop_tasks.aggregate(
		total=Sum('completed_quantity')
	)['total'] or 0
	
	total_defective = workshop_tasks.aggregate(
		total=Sum('defective_quantity')
	)['total'] or 0
	
	workshop_summary = {
		'id': workshop.id,
		'name': workshop.name,
		'description': workshop.description,
		'employees_count': employees.count(),
		'active_orders': active_orders.count(),
		'products_made_30_days': total_completed,
		'defective_products_30_days': total_defective,
		'quality_rate': round((total_completed - total_defective) / total_completed * 100, 1) if total_completed > 0 else 100
	}
	
	return Response({
		'workshop': workshop_summary,
		'employees': employees_stats,
		'orders': orders_stats
	})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def workshop_orders_info(request, workshop_id):
	"""
	Получает информацию о заказах в конкретном цехе с полной информацией о товарах
	"""
	try:
		workshop = Workshop.objects.get(id=workshop_id)
		orders_info = workshop.get_orders_info()
		workshop_summary = workshop.get_workshop_summary()
		
		return Response({
			'workshop': workshop_summary,
			'orders': orders_info
		})
	except Workshop.DoesNotExist:
		return Response({'error': 'Цех не найден'}, status=404)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def all_workshops_orders_info(request):
	"""
	Получает информацию о заказах во всех цехах
	"""
	workshops = Workshop.objects.filter(is_active=True)
	result = []
	
	for workshop in workshops:
		workshop_summary = workshop.get_workshop_summary()
		orders_info = workshop.get_orders_info()
		
		result.append({
			'workshop': workshop_summary,
			'orders': orders_info
		})
	
	return Response(result)

def workshops_page(request):
	return render(request, 'workshops.html')

def workshops_mobile_page(request):
	return render(request, 'workshops_mobile.html')

def master_dashboard_page(request):
	"""
	Страница дашборда мастера с обзором всех его цехов
	"""
	if request.user.role != 'master':
		# Перенаправляем на обычную страницу цехов
		return workshops_list(request)
	
	# Простая проверка мобильного устройства по User-Agent
	user_agent = request.META.get('HTTP_USER_AGENT', '')
	ua_lower = user_agent.lower()
	is_mobile = any(token in ua_lower for token in ['mobile', 'android', 'iphone', 'ipad'])
	
	if is_mobile:
		return render(request, 'workshop_mobile.html')
	
	return render(request, 'workshop_master.html')

def workshops_list(request):
	from apps.employees.models import EmployeeStatistics
	from apps.employee_tasks.models import EmployeeTask
	from apps.defects.models import Defect
	from django.db.models import Q, Count, Avg
	
	# Простая проверка мобильного устройства по User-Agent
	user_agent = request.META.get('HTTP_USER_AGENT', '')
	ua_lower = user_agent.lower()
	is_mobile = any(token in ua_lower for token in ['mobile', 'android', 'iphone', 'ipad'])
	if is_mobile:
		return render(request, 'workshops_mobile.html')
	
	# Получаем все активные цеха с предзагрузкой связанных данных
	workshops = Workshop.objects.filter(is_active=True).prefetch_related(
		'users', 
		'workshop_masters__master',
		'manager'
	)
	
	# Подготавливаем данные для каждого цеха
	workshops_data = []
	for workshop in workshops:
		# Подсчитываем сотрудников в цехе
		employees_count = workshop.users.count() if hasattr(workshop, 'users') else 0
		
		# Подсчитываем активные задачи
		active_tasks = EmployeeTask.objects.filter(stage__workshop=workshop).count()
		
		# Подсчитываем браки
		defects = Defect.objects.filter(user__workshop=workshop).count()
		
		# Вычисляем производительность (примерно)
		productivity = active_tasks * 10  # Упрощенный расчет
		
		# Создаем график производительности (случайные данные)
		import random
		productivity_chart = [random.randint(1, 7) for _ in range(7)]
		
		# Получаем информацию о мастерах
		workshop_masters = workshop.workshop_masters.filter(is_active=True)
		
		workshops_data.append({
			'id': workshop.id,
			'name': workshop.name,
			'description': workshop.description,
			'manager': workshop.manager.get_full_name() if workshop.manager else 'Не назначен',
			'created_at': workshop.created_at,
			'updated_at': workshop.updated_at,
			'employees_count': employees_count,
			'active_tasks': active_tasks,
			'defects': defects,
			'productivity': productivity,
			'productivity_chart': productivity_chart,
			'workshop_masters': workshop_masters,  # Добавляем информацию о мастерах
		})
	
	# Общая статистика
	total_workshops = workshops.count()
	total_employees = sum(w['employees_count'] for w in workshops_data)
	total_active_tasks = sum(w['active_tasks'] for w in workshops_data)
	avg_productivity = sum(w['productivity'] for w in workshops_data) // max(total_workshops, 1)
	
	context = {
		'workshops': workshops_data,
		'total_workshops': total_workshops,
		'total_employees': total_employees,
		'total_active_tasks': total_active_tasks,
		'avg_productivity': avg_productivity,
	}
	
	return render(request, 'workshops.html', context)
