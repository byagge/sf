from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from apps.operations.workshops.models import Workshop
from apps.employee_tasks.models import EmployeeTask
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta

User = get_user_model()

class MyWorkshopsView(APIView):
	permission_classes = [IsAuthenticated]
	def get(self, request):
		# Получаем цеха, которыми управляет пользователь (главный мастер или дополнительный)
		workshops = []
		
		# Цеха, где пользователь является главным мастером
		managed_workshops = request.user.operation_managed_workshops.all()
		for workshop in managed_workshops:
			workshops.append({
				'id': workshop.id, 
				'name': workshop.name,
				'role': 'main_manager'
			})
		
		# Цеха, где пользователь является дополнительным мастером
		additional_workshops = request.user.workshop_master_roles.filter(is_active=True).select_related('workshop')
		for workshop_master in additional_workshops:
			workshops.append({
				'id': workshop_master.workshop.id, 
				'name': workshop_master.workshop.name,
				'role': 'additional_master'
			})
		
		return Response(workshops)

class WorkshopEmployeesView(APIView):
	permission_classes = [IsAuthenticated]
	def get(self, request):
		workshop_id = request.GET.get('workshop')
		employees = User.objects.filter(workshop_id=workshop_id)
		return Response([{'id': e.id, 'name': e.get_full_name()} for e in employees])

class AllWorkshopsView(APIView):
	permission_classes = [IsAuthenticated]
	def get(self, request):
		workshops = Workshop.objects.filter(is_active=True).order_by('name', 'id')
		workshops_data = []
		
		for workshop in workshops:
			# Получаем всех мастеров цеха
			all_masters = workshop.get_all_masters()
			master_info = []
			
			# Главный мастер
			if workshop.manager:
				master_info.append({
					'id': workshop.manager.id,
					'name': workshop.manager.get_full_name(),
					'role': 'main_manager'
				})
			
			# Дополнительные мастера
			additional_masters = workshop.workshop_masters.filter(is_active=True).select_related('master')
			for wm in additional_masters:
				master_info.append({
					'id': wm.master.id,
					'name': wm.master.get_full_name(),
					'role': 'additional_master'
				})
			
			workshops_data.append({
				'id': workshop.id,
				'name': workshop.name,
				'masters': master_info,
				'master_count': len(master_info)
			})
		
		return Response(workshops_data)

class WorkshopMastersView(APIView):
	permission_classes = [IsAuthenticated]
	def get(self, request):
		"""Получает список всех мастеров конкретного цеха"""
		workshop_id = request.GET.get('workshop')
		if not workshop_id:
			return Response({'error': 'Не указан ID цеха'}, status=400)
		
		try:
			workshop = Workshop.objects.get(id=workshop_id, is_active=True)
		except Workshop.DoesNotExist:
			return Response({'error': 'Цех не найден'}, status=404)
		
		# Получаем всех мастеров цеха
		all_masters = workshop.get_all_masters()
		masters_data = []
		
		# Главный мастер
		if workshop.manager:
			masters_data.append({
				'id': workshop.manager.id,
				'name': workshop.manager.get_full_name(),
				'role': 'main_manager',
				'can_remove': False
			})
		
		# Дополнительные мастера
		additional_masters = workshop.workshop_masters.filter(is_active=True).select_related('master')
		for wm in additional_masters:
			masters_data.append({
				'id': wm.master.id,
				'name': wm.master.get_full_name(),
				'role': 'additional_master',
				'can_remove': True,
				'added_at': wm.added_at,
				'notes': wm.notes
			})
		
		return Response(masters_data)

class AddWorkshopMasterView(APIView):
	permission_classes = [IsAuthenticated]
	def post(self, request):
		"""Добавляет дополнительного мастера к цеху"""
		workshop_id = request.data.get('workshop_id')
		master_id = request.data.get('master_id')
		
		if not workshop_id or not master_id:
			return Response({'error': 'Не указаны ID цеха или мастера'}, status=400)
		
		try:
			workshop = Workshop.objects.get(id=workshop_id, is_active=True)
			master = User.objects.get(id=master_id)
		except (Workshop.DoesNotExist, User.DoesNotExist):
			return Response({'error': 'Цех или мастер не найден'}, status=404)
		
		# Проверяем права доступа (только главный мастер может добавлять других мастеров)
		if not workshop.is_user_master(request.user) or workshop.manager != request.user:
			return Response({'error': 'Недостаточно прав для добавления мастера'}, status=403)
		
		# Добавляем мастера
		success, message = workshop.add_master(master)
		
		if success:
			return Response({'message': message, 'success': True})
		else:
			return Response({'error': message}, status=400)

class RemoveWorkshopMasterView(APIView):
	permission_classes = [IsAuthenticated]
	def post(self, request):
		"""Удаляет дополнительного мастера из цеха"""
		workshop_id = request.data.get('workshop_id')
		master_id = request.data.get('master_id')
		
		if not workshop_id or not master_id:
			return Response({'error': 'Не указаны ID цеха или мастера'}, status=400)
		
		try:
			workshop = Workshop.objects.get(id=workshop_id, is_active=True)
			master = User.objects.get(id=master_id)
		except (Workshop.DoesNotExist, User.DoesNotExist):
			return Response({'error': 'Цех или мастер не найден'}, status=404)
		
		# Проверяем права доступа (только главный мастер может удалять других мастеров)
		if not workshop.is_user_master(request.user) or workshop.manager != request.user:
			return Response({'error': 'Недостаточно прав для удаления мастера'}, status=403)
		
		# Удаляем мастера
		success, message = workshop.remove_master(master)
		
		if success:
			return Response({'message': message, 'success': True})
		else:
			return Response({'error': message}, status=400) 

class MasterWorkshopsStatsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Получает статистику по всем цехам мастера"""
        user = request.user
        
        # Получаем все цеха мастера
        master_workshops = []
        
        # Цеха, где пользователь является главным мастером
        managed_workshops = user.operation_managed_workshops.filter(is_active=True)
        for workshop in managed_workshops:
            master_workshops.append(workshop)
        
        # Цеха, где пользователь является дополнительным мастером
        additional_workshops = user.workshop_master_roles.filter(is_active=True, workshop__is_active=True).select_related('workshop')
        for workshop_master in additional_workshops:
            master_workshops.append(workshop_master.workshop)
        
        # Убираем дубликаты
        master_workshops = list(set(master_workshops))
        
        # Периоды для статистики
        now = timezone.now()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        
        # Общая статистика по всем цехам мастера
        total_stats = self._calculate_total_stats(master_workshops, week_ago, month_ago)
        
        # Статистика по каждому цеху
        workshops_stats = []
        for workshop in master_workshops:
            workshop_stats = self._calculate_workshop_stats(workshop, week_ago, month_ago)
            workshops_stats.append(workshop_stats)
        
        return Response({
            'total_stats': total_stats,
            'workshops': workshops_stats
        })
    
    def _calculate_total_stats(self, workshops, week_ago, month_ago):
        """Рассчитывает общую статистику по всем цехам мастера"""
        # Получаем все задачи по цехам мастера
        workshop_ids = [w.id for w in workshops]
        all_tasks = EmployeeTask.objects.filter(stage__workshop_id__in=workshop_ids)
        
        # Статистика за неделю
        week_tasks = all_tasks.filter(created_at__gte=week_ago)
        week_completed = week_tasks.aggregate(
            total=Sum('completed_quantity'),
            defects=Sum('defective_quantity')
        )
        
        # Статистика за месяц
        month_tasks = all_tasks.filter(created_at__gte=month_ago)
        month_completed = month_tasks.aggregate(
            total=Sum('completed_quantity'),
            defects=Sum('defective_quantity')
        )
        
        # Общая статистика
        total_completed = all_tasks.aggregate(
            total=Sum('completed_quantity'),
            defects=Sum('defective_quantity')
        )
        
        # Количество сотрудников
        total_employees = sum(w.users.count() for w in workshops)
        
        # Эффективность (процент выполненных задач без брака)
        total_quantity = all_tasks.aggregate(total=Sum('quantity'))['total'] or 0
        total_completed_quantity = total_completed['total'] or 0
        total_defects = total_completed['defects'] or 0
        
        efficiency = 0
        if total_quantity > 0:
            efficiency = round(((total_completed_quantity - total_defects) / total_quantity) * 100, 1)
        
        return {
            'total_workshops': len(workshops),
            'total_employees': total_employees,
            'week_stats': {
                'completed_works': week_completed['total'] or 0,
                'defects': week_completed['defects'] or 0,
                'efficiency': self._calculate_efficiency(week_completed['total'] or 0, week_completed['defects'] or 0)
            },
            'month_stats': {
                'completed_works': month_completed['total'] or 0,
                'defects': month_completed['defects'] or 0,
                'efficiency': self._calculate_efficiency(month_completed['total'] or 0, month_completed['defects'] or 0)
            },
            'total_stats': {
                'completed_works': total_completed_quantity,
                'defects': total_defects,
                'efficiency': efficiency
            }
        }
    
    def _calculate_workshop_stats(self, workshop, week_ago, month_ago):
        """Рассчитывает статистику по конкретному цеху"""
        # Получаем задачи цеха
        workshop_tasks = EmployeeTask.objects.filter(stage__workshop=workshop)
        
        # Статистика за неделю
        week_tasks = workshop_tasks.filter(created_at__gte=week_ago)
        week_completed = week_tasks.aggregate(
            total=Sum('completed_quantity'),
            defects=Sum('defective_quantity')
        )
        
        # Статистика за месяц
        month_tasks = workshop_tasks.filter(created_at__gte=month_ago)
        month_completed = month_tasks.aggregate(
            total=Sum('completed_quantity'),
            defects=Sum('defective_quantity')
        )
        
        # Общая статистика
        total_completed = workshop_tasks.aggregate(
            total=Sum('completed_quantity'),
            defects=Sum('defective_quantity')
        )
        
        # Количество сотрудников
        employees_count = workshop.users.count()
        
        # Эффективность
        total_quantity = workshop_tasks.aggregate(total=Sum('quantity'))['total'] or 0
        total_completed_quantity = total_completed['total'] or 0
        total_defects = total_completed['defects'] or 0
        
        efficiency = 0
        if total_quantity > 0:
            efficiency = round(((total_completed_quantity - total_defects) / total_quantity) * 100, 1)
        
        return {
            'id': workshop.id,
            'name': workshop.name,
            'description': workshop.description,
            'employees_count': employees_count,
            'week_stats': {
                'completed_works': week_completed['total'] or 0,
                'defects': week_completed['defects'] or 0,
                'efficiency': self._calculate_efficiency(week_completed['total'] or 0, week_completed['defects'] or 0)
            },
            'month_stats': {
                'completed_works': month_completed['total'] or 0,
                'defects': month_completed['defects'] or 0,
                'efficiency': self._calculate_efficiency(month_completed['total'] or 0, month_completed['defects'] or 0)
            },
            'total_stats': {
                'completed_works': total_completed_quantity,
                'defects': total_defects,
                'efficiency': efficiency
            }
        }
    
    def _calculate_efficiency(self, completed, defects):
        """Рассчитывает эффективность в процентах"""
        if completed == 0:
            return 0
        return round(((completed - defects) / completed) * 100, 1) 