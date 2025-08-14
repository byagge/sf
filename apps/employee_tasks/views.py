from django.shortcuts import render
from rest_framework import viewsets, permissions, filters
from .models import EmployeeTask
from .serializers import EmployeeTaskSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from apps.employees.models import EmployeeDocument
from apps.employees.serializers import EmployeeSerializer
from apps.orders.models import OrderDefect

# Create your views here.

class EmployeeTaskViewSet(viewsets.ModelViewSet):
    queryset = EmployeeTask.objects.all().order_by('-created_at')
    serializer_class = EmployeeTaskSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'employee__first_name', 'employee__last_name', 'order__name']
    ordering_fields = ['created_at', 'is_completed', 'plan_quantity', 'completed_quantity']

    def get_queryset(self):
        queryset = super().get_queryset()
        employee_id = self.request.query_params.get('employee')
        order_id = self.request.query_params.get('order')
        if employee_id:
            queryset = queryset.filter(employee_id=employee_id)
        if order_id:
            queryset = queryset.filter(order_id=order_id)
        return queryset

    def update(self, request, *args, **kwargs):
        """Переопределяем update для автоматического создания OrderDefect при фиксации брака"""
        instance = self.get_object()
        old_defective_quantity = instance.defective_quantity
        
        # Вызываем родительский метод update
        response = super().update(request, *args, **kwargs)
        
        # Проверяем, изменилось ли количество брака
        instance.refresh_from_db()
        new_defective_quantity = instance.defective_quantity
        
        if new_defective_quantity > old_defective_quantity:
            # Создаём запись в OrderDefect
            defect_quantity = new_defective_quantity - old_defective_quantity
            OrderDefect.objects.create(
                order=instance.stage.order,
                workshop=instance.stage.workshop,
                quantity=defect_quantity,
                comment=f"Брак зафиксирован сотрудником {instance.employee.get_full_name() or instance.employee.username} в задаче"
            )
        
        return response

class EmployeeFullInfoAPIView(APIView):
    def get(self, request, pk):
        # Получить сотрудника
        from apps.users.models import User
        try:
            employee = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({'detail': 'Not found'}, status=404)
        # Основная информация
        employee_data = EmployeeSerializer(employee).data
        # Задачи
        tasks = EmployeeTask.objects.filter(employee=employee)
        employee_data['tasks'] = EmployeeTaskSerializer(tasks, many=True).data
        # Документы
        docs = EmployeeDocument.objects.filter(employee=employee)
        employee_data['documents'] = [
            {
                'id': doc.id,
                'document_type': doc.document_type,
                'document_type_display': doc.get_document_type_display(),
                'status': doc.status,
                'status_display': doc.get_status_display(),
                'expiry_date': doc.expiry_date.isoformat() if doc.expiry_date else None,
                'uploaded_at': doc.uploaded_at.isoformat() if doc.uploaded_at else None
            }
            for doc in docs
        ]
        return Response(employee_data)

def tasks_page(request):
    return render(request, 'tasks.html')

def employee_info_page(request):
    return render(request, 'employee_info.html')

def stats_employee_page(request):
    return render(request, 'stats_employee.html')

def defects_management_page(request):
    """Страница управления браком"""
    return render(request, 'defects_management.html')
