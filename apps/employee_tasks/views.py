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
    queryset = EmployeeTask.objects.select_related(
        'stage__order_item__product', 
        'stage__workshop', 
        'stage__order',
        'stage__order__client',
        'employee'
    ).prefetch_related(
        'stage__order_item__product__services'
    ).all().order_by('-created_at')
    serializer_class = EmployeeTaskSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = [
        'stage__operation', 
        'stage__order_item__product__name',
        'employee__first_name', 
        'employee__last_name', 
        'stage__order__name'
    ]
    ordering_fields = ['created_at', 'completed_quantity', 'quantity']

    def get_queryset(self):
        queryset = super().get_queryset()
        employee_id = self.request.query_params.get('employee')
        order_id = self.request.query_params.get('order')
        stage_id = self.request.query_params.get('stage')
        
        if employee_id:
            queryset = queryset.filter(employee_id=employee_id)
        if order_id:
            queryset = queryset.filter(stage__order_id=order_id)
        if stage_id:
            queryset = queryset.filter(stage_id=stage_id)
            
        return queryset

    def update(self, request, *args, **kwargs):
        """Переопределяем update для обработки изменений задачи"""
        # Вызываем родительский метод update
        response = super().update(request, *args, **kwargs)
        
        # Браки теперь создаются автоматически через сигнал pre_save
        # при изменении defective_quantity
        
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

def task_detail_page(request, task_id):
    """Страница детального просмотра задачи"""
    return render(request, 'task_detail.html', {
        'task_id': task_id
    })
