from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.db import transaction
from django.db.models import F
import json
from .models import EmployeeTask, HelperTask
from apps.users.models import User

@login_required
def task_list(request):
    """Список задач для сотрудника или помощника"""
    user = request.user
    
    if user.is_helper():
        # Для помощника показываем задачи помощи
        tasks = HelperTask.objects.filter(helper=user).select_related(
            'employee_task__employee', 'employee_task__stage__workshop', 
            'employee_task__stage__order', 'employee_task__stage__order_item__product'
        ).prefetch_related('employee_task__stage__order__client')
    else:
        # Для обычного сотрудника показываем его задачи
        tasks = EmployeeTask.objects.filter(employee=user).select_related(
            'stage__workshop', 'stage__order', 'stage__order_item__product'
        ).prefetch_related('stage__order__client')
    
    context = {
        'tasks': tasks,
        'is_helper': user.is_helper()
    }
    
    return render(request, 'tasks.html', context)

@login_required
def task_detail(request, task_id):
    """Детальная информация о задаче (отрисовывается на клиенте)"""
    # Флаг помощника: роль пользователя или query (?helper=1)
    is_helper_flag = request.user.is_helper() or request.GET.get('helper') in ('1', 'true', 'True')
    context = {
        'task_id': task_id,
        'is_helper': is_helper_flag,
    }
    return render(request, 'task_detail.html', context)

@login_required
def stats_view(request):
    """Статистика для сотрудника или помощника"""
    user = request.user
    
    if user.is_helper():
        # Статистика помощника
        helper_tasks = HelperTask.objects.filter(helper=user)
        total_earnings = sum(task.net_earnings for task in helper_tasks)
        total_tasks = helper_tasks.count()
        completed_tasks = helper_tasks.filter(completed_quantity__gte=F('quantity')).count()
        
        context = {
            'total_earnings': total_earnings,
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'is_helper': True
        }
    else:
        # Статистика обычного сотрудника
        employee_tasks = EmployeeTask.objects.filter(employee=user)
        total_earnings = sum(task.net_earnings for task in employee_tasks)
        total_tasks = employee_tasks.count()
        completed_tasks = employee_tasks.filter(completed_quantity__gte=F('quantity')).count()
        
        context = {
            'total_earnings': total_earnings,
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'is_helper': False
        }
    
    return render(request, 'stats_employee.html', context)

@login_required
def assign_task(request):
    """Назначение задачи (только для мастеров)"""
    if not request.user.role == User.Role.MASTER:
        messages.error(request, 'У вас нет прав для назначения задач')
        return redirect('employee_tasks:task_list')
    
    if request.method == 'POST':
        data = json.loads(request.body)
        employee_id = data.get('employee')
        stage_id = data.get('stage')
        quantity = data.get('quantity', 1)
        
        try:
            with transaction.atomic():
                employee_task = EmployeeTask.objects.create(
                    employee_id=employee_id,
                    stage_id=stage_id,
                    quantity=quantity
                )
                return JsonResponse({'status': 'success', 'id': employee_task.id})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid method'})

@login_required
def edit_assignment(request, assignment_id):
    """Редактирование назначения (только для мастеров)"""
    if not request.user.role == User.Role.MASTER:
        messages.error(request, 'У вас нет прав для редактирования задач')
        return redirect('employee_tasks:task_list')
    
    assignment = get_object_or_404(EmployeeTask, id=assignment_id)
    
    if request.method == 'PATCH':
        data = json.loads(request.body)
        quantity = data.get('quantity')
        
        if quantity is not None:
            assignment.quantity = quantity
            assignment.save()
            return JsonResponse({'status': 'success'})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid method'})

# API endpoints для помощника
@login_required
@csrf_exempt
@require_http_methods(["POST"])
def create_helper_task(request):
    """Создание задачи помощника"""
    if not request.user.is_helper():
        return JsonResponse({'error': 'Only helpers can create helper tasks'}, status=403)
    
    try:
        data = json.loads(request.body)
        employee_task_id = data.get('employee_task')
        quantity = data.get('quantity', 1)
        
        employee_task = get_object_or_404(EmployeeTask, id=employee_task_id)
        
        # Проверяем, что помощник находится в том же цехе
        if employee_task.stage.workshop != request.user.workshop:
            return JsonResponse({'error': 'You can only help in your own workshop'}, status=403)
        
        # Проверяем, что задача еще не имеет помощника
        if HelperTask.objects.filter(employee_task=employee_task, helper=request.user).exists():
            return JsonResponse({'error': 'You are already helping with this task'}, status=400)
        
        helper_task = HelperTask.objects.create(
            employee_task=employee_task,
            helper=request.user,
            quantity=quantity
        )
        
        return JsonResponse({'status': 'success', 'id': helper_task.id})
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@csrf_exempt
@require_http_methods(["PATCH"])
def update_helper_task(request, task_id):
    """Обновление задачи помощника"""
    helper_task = get_object_or_404(HelperTask, id=task_id, helper=request.user)
    
    try:
        data = json.loads(request.body)
        completed_quantity = data.get('completed_quantity')
        defective_quantity = data.get('defective_quantity')
        
        if completed_quantity is not None:
            helper_task.completed_quantity = completed_quantity
        if defective_quantity is not None:
            helper_task.defective_quantity = defective_quantity
        
        helper_task.save()
        return JsonResponse({'status': 'success'})
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
