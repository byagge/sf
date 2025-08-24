from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from apps.operations.workshops.models import Workshop

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