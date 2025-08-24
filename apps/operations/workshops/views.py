from django.shortcuts import render
from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
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
