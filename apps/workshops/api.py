from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from apps.operations.workshops.models import Workshop

User = get_user_model()

class MyWorkshopsView(APIView):
	permission_classes = [IsAuthenticated]
	def get(self, request):
		# Получаем цеха, которыми управляет пользователь (мастер)
		workshops = request.user.operation_managed_workshops.all()
		return Response([{'id': w.id, 'name': w.name} for w in workshops])

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
		return Response([{'id': w.id, 'name': w.name} for w in workshops]) 