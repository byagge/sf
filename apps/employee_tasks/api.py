from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Sum, Count, F, OuterRef, Subquery, DecimalField, ExpressionWrapper
from django.db.models.functions import ExtractMonth, ExtractYear, Coalesce
from django.contrib.auth import get_user_model
from .models import EmployeeTask
from apps.services.models import Service
from .serializers import EmployeeTaskSerializer

User = get_user_model()
 
class EmployeeTaskAssignViewSet(viewsets.ModelViewSet):
    queryset = EmployeeTask.objects.all().order_by('-created_at', 'id')
    serializer_class = EmployeeTaskSerializer
 
    
    def create(self, request, *args, **kwargs):
        try:
            from django.db.models import Sum
            from apps.orders.models import OrderStage
            from decimal import Decimal
            
            stage_id = request.data.get('stage')
            employee_id = request.data.get('employee')
            try:
                quantity = int(request.data.get('quantity', 0))
            except Exception:
                quantity = 0
            # Поддержка обоих названий поля
            custom_service_price = request.data.get('custom_service_price')
            if custom_service_price is None:
                custom_service_price = request.data.get('price')
            try:
                custom_service_price = (Decimal(str(custom_service_price)) if custom_service_price not in (None, '',) else None)
            except Exception:
                return Response({'error': 'Неверный формат цены'}, status=400)
            
            if not stage_id or not employee_id:
                return Response({'error': 'Необходимо указать stage и employee'}, status=400)
            
            # Получаем этап и план
            try:
                stage = OrderStage.objects.get(id=stage_id)
            except OrderStage.DoesNotExist:
                return Response({'error': 'Этап не найден'}, status=404)
            
            plan = int(stage.plan_quantity or 0)
            if plan <= 0:
                return Response({'error': 'План этапа равен 0'}, status=400)
            
            # Сколько уже назначено по этапу (всех задач суммарно)
            already_assigned = EmployeeTask.objects.filter(stage=stage).aggregate(s=Sum('quantity'))['s'] or 0
            remaining = max(0, plan - int(already_assigned))
            if remaining <= 0:
                return Response({'error': 'План уже полностью распределен'}, status=400)
            
            # Количество не может превышать остаток и должно быть >=1
            if quantity <= 0:
                return Response({'error': 'Количество должно быть больше 0'}, status=400)
            if quantity > remaining:
                quantity = remaining
            
            # Разрешаем только ОДНУ задачу на (stage, employee): upsert
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                employee = User.objects.get(id=employee_id)
            except User.DoesNotExist:
                return Response({'error': 'Сотрудник не найден'}, status=404)
            
            task, created = EmployeeTask.objects.get_or_create(
                stage=stage,
                employee=employee,
                defaults={
                    'quantity': quantity,
                    'custom_service_price': custom_service_price
                }
            )
            if not created:
                # Увеличиваем количество, но не превышая общий план
                new_qty = int(task.quantity or 0) + quantity
                # Пересчитываем остаток с учетом текущей задачи
                already_assigned_excluding_current = (already_assigned - int(task.quantity or 0))
                max_allowed_for_task = max(0, plan - already_assigned_excluding_current)
                task.quantity = min(new_qty, max_allowed_for_task)
                # Обновляем кастомную цену, если передана
                if custom_service_price is not None:
                    task.custom_service_price = custom_service_price
                task.save(update_fields=['quantity', 'custom_service_price'] if custom_service_price is not None else ['quantity'])
            
            serializer = self.get_serializer(task)
            status_code = 201 if created else 200
            return Response(serializer.data, status=status_code)
        except Exception as e:
            return Response({'error': str(e)}, status=500)

    def partial_update(self, request, *args, **kwargs):
        try:
            from decimal import Decimal
            task = self.get_object()
            # Разрешаем обновление количества, выполненного/брака и индивидуальной цены
            data = request.data or {}
            fields_to_update = []
            if 'quantity' in data:
                try:
                    task.quantity = int(data.get('quantity') or 0)
                    fields_to_update.append('quantity')
                except Exception:
                    return Response({'error': 'Неверное количество'}, status=400)
            if 'completed_quantity' in data:
                try:
                    task.completed_quantity = int(data.get('completed_quantity') or 0)
                    fields_to_update.append('completed_quantity')
                except Exception:
                    return Response({'error': 'Неверное выполненное количество'}, status=400)
            if 'defective_quantity' in data:
                try:
                    task.defective_quantity = int(data.get('defective_quantity') or 0)
                    fields_to_update.append('defective_quantity')
                except Exception:
                    return Response({'error': 'Неверное количество брака'}, status=400)
            # Поддержка обоих названий поля
            custom_service_price = data.get('custom_service_price')
            if custom_service_price is None and 'price' in data:
                custom_service_price = data.get('price')
            if custom_service_price is not None:
                if custom_service_price == '' or custom_service_price is None:
                    task.custom_service_price = None
                else:
                    try:
                        task.custom_service_price = Decimal(str(custom_service_price))
                    except Exception:
                        return Response({'error': 'Неверный формат цены'}, status=400)
                fields_to_update.append('custom_service_price')
            
            if not fields_to_update:
                return Response({'error': 'Нет данных для обновления'}, status=400)
            task.save(update_fields=fields_to_update)
            serializer = self.get_serializer(task)
            return Response(serializer.data)
        except Exception as e:
            return Response({'error': str(e)}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def employee_earnings_stats(request, employee_id):
    """Статистика заработка конкретного сотрудника"""
    try:
        employee = User.objects.get(id=employee_id)
        
        # Базовый queryset задач сотрудника
        tasks = EmployeeTask.objects.filter(employee=employee)
        
        # Простая статистика без сложных вычислений
        total_tasks = tasks.count()
        completed_tasks = tasks.filter(completed_quantity__gt=0).count()
        
        # Пробуем получить базовые суммы
        try:
            total_earnings = tasks.aggregate(s=Sum('earnings'))['s'] or 0
            total_penalties = tasks.aggregate(s=Sum('penalties'))['s'] or 0
            total_net_earnings = tasks.aggregate(s=Sum('net_earnings'))['s'] or 0
            
            # Отладочная информация
            print(f"Employee {employee.username}: total_earnings={total_earnings}, total_penalties={total_penalties}, total_net={total_net_earnings}")
            
            # Проверяем отдельные задачи
            for task in tasks[:5]:  # Первые 5 задач для отладки
                print(f"Task {task.id}: earnings={task.earnings}, penalties={task.penalties}, net={task.net_earnings}, completed={task.completed_quantity}, service={task.service}")
                
        except Exception as e:
            print(f"Error aggregating earnings: {e}")
            total_earnings = 0
            total_penalties = 0
            total_net_earnings = 0
        
        # Простая статистика по цехам
        try:
            workshop_stats = list(tasks.values('stage__workshop__name').annotate(
            total_earnings=Sum('earnings'),
            total_penalties=Sum('penalties'),
            total_net=Sum('net_earnings'),
            task_count=Count('id')
            ))
        except Exception as e:
            print(f"Error with workshop stats: {e}")
            workshop_stats = []
        
        # Простая статистика по месяцам
        try:
            monthly_stats = list(
                tasks
                .annotate(year=ExtractYear('created_at'), month=ExtractMonth('created_at'))
                .values('year', 'month')
                .annotate(
            total_earnings=Sum('earnings'),
            total_penalties=Sum('penalties'),
            total_net=Sum('net_earnings'),
            task_count=Count('id')
                )
                .order_by('year', 'month')
            )
        except Exception as e:
            print(f"Error with monthly stats: {e}")
            monthly_stats = []
        
        return Response({
            'employee': {
                'id': employee.id,
                'name': employee.get_full_name() or employee.username,
                'username': employee.username
            },
            'overview': {
                'total_earnings': total_earnings,
                'total_penalties': total_penalties,
                'total_net_earnings': total_net_earnings,
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks
            },
            'balance': employee.balance,
            'workshop_stats': workshop_stats,
            'monthly_stats': monthly_stats
        })
        
    except User.DoesNotExist:
        return Response({'error': 'Сотрудник не найден'}, status=404)
    except Exception as e:
        print(f"Error in employee_earnings_stats: {e}")
        import traceback
        traceback.print_exc()
        return Response({'error': str(e)}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def workshop_earnings_stats(request, workshop_id):
    """Статистика заработка по цеху"""
    try:
        from apps.operations.workshops.models import Workshop
        workshop = Workshop.objects.get(id=workshop_id)
        
        # Базовый queryset по цеху
        tasks = EmployeeTask.objects.filter(stage__workshop=workshop)
        
        # Простая статистика
        try:
            total_earnings = tasks.aggregate(s=Sum('earnings'))['s'] or 0
            total_penalties = tasks.aggregate(s=Sum('penalties'))['s'] or 0
            total_net_earnings = tasks.aggregate(s=Sum('net_earnings'))['s'] or 0
        except Exception as e:
            print(f"Error aggregating workshop earnings: {e}")
            total_earnings = 0
            total_penalties = 0
            total_net_earnings = 0
        
        # Статистика по сотрудникам
        try:
            employee_stats = list(tasks.values('employee__username', 'employee__first_name', 'employee__last_name').annotate(
            total_earnings=Sum('earnings'),
            total_penalties=Sum('penalties'),
            total_net=Sum('net_earnings'),
            task_count=Count('id')
            ))
        except Exception as e:
            print(f"Error with employee stats: {e}")
            employee_stats = []
        
        # Получаем услугу цеха
        try:
            service = Service.objects.get(workshop=workshop, is_active=True)
            service_info = {
                'name': service.name,
                'price': service.service_price,
                'defect_penalty': service.defect_penalty
            }
        except Service.DoesNotExist:
            service_info = None
        
        return Response({
            'workshop': {
                'id': workshop.id,
                'name': workshop.name
            },
            'overview': {
                'total_earnings': total_earnings,
                'total_penalties': total_penalties,
                'total_net_earnings': total_net_earnings,
                'total_tasks': tasks.count()
            },
            'employee_stats': employee_stats,
            'service': service_info
        })
        
    except Workshop.DoesNotExist:
        return Response({'error': 'Цех не найден'}, status=404)
    except Exception as e:
        print(f"Error in workshop_earnings_stats: {e}")
        import traceback
        traceback.print_exc()
        return Response({'error': str(e)}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def top_earners(request):
    """Топ сотрудников по заработку"""
    try:
        # Получаем топ-10 сотрудников по чистому заработку
        top_employees = EmployeeTask.objects.values(
            'employee__username', 
            'employee__first_name', 
            'employee__last_name'
        ).annotate(
            total_earnings=Sum('earnings'),
            total_penalties=Sum('penalties'),
            total_net=Sum('net_earnings'),
            task_count=Count('id')
        ).order_by('-total_net')[:10]
        
        return Response({
            'top_earners': top_employees
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=500) 

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def approve_defect_rework(request, defect_id):
    """Админ разрешает переработку брака"""
    try:
        from apps.orders.models import OrderDefect
        
        defect = OrderDefect.objects.get(id=defect_id)
        comment = request.data.get('comment', '')
        deadline = request.data.get('deadline')
        
        if deadline:
            from datetime import datetime
            deadline = datetime.strptime(deadline, '%Y-%m-%d').date()
        
        success, message = defect.approve_for_rework(
            admin_user=request.user,
            comment=comment,
            deadline=deadline
        )
        
        if success:
            return Response({'success': True, 'message': message})
        else:
            return Response({'success': False, 'error': message}, status=400)
            
    except OrderDefect.DoesNotExist:
        return Response({'error': 'Брак не найден'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_defect_rework(request, defect_id):
    """Начинает переработку брака"""
    try:
        from apps.orders.models import OrderDefect
        
        defect = OrderDefect.objects.get(id=defect_id)
        employee_id = request.data.get('employee_id')
        try:
            employee_id = int(employee_id)
        except Exception:
            return Response({'error': 'Некорректный сотрудник'}, status=400)
        
        from django.contrib.auth import get_user_model
        User = get_user_model()
        employee = User.objects.get(id=employee_id)
        
        success, message = defect.start_rework(employee)
        
        if success:
            return Response({'success': True, 'message': message})
        else:
            return Response({'success': False, 'error': message}, status=400)
            
    except OrderDefect.DoesNotExist:
        return Response({'error': 'Брак не найден'}, status=404)
    except User.DoesNotExist:
        return Response({'error': 'Сотрудник не найден'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def complete_defect_rework(request, defect_id):
    """Завершает переработку брака"""
    try:
        from apps.orders.models import OrderDefect
        
        defect = OrderDefect.objects.get(id=defect_id)
        try:
            completed_quantity = int(request.data.get('completed_quantity', 0))
            defective_quantity = int(request.data.get('defective_quantity', 0))
        except Exception:
            return Response({'error': 'Некорректные количества'}, status=400)
        
        success, message = defect.complete_rework(
            completed_quantity=completed_quantity,
            defective_quantity=defective_quantity
        )
        
        if success:
            return Response({'success': True, 'message': message})
        else:
            return Response({'success': False, 'error': message}, status=400)
            
    except OrderDefect.DoesNotExist:
        return Response({'error': 'Брак не найден'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reject_defect(request, defect_id):
    """Админ отклоняет брак (списывает в убытки)"""
    try:
        from apps.orders.models import OrderDefect
        
        defect = OrderDefect.objects.get(id=defect_id)
        comment = request.data.get('comment', '')
        
        success, message = defect.reject_defect(
            admin_user=request.user,
            comment=comment
        )
        
        if success:
            return Response({'success': True, 'message': message})
        else:
            return Response({'success': False, 'error': message}, status=400)
            
    except OrderDefect.DoesNotExist:
        return Response({'error': 'Брак не найден'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def defects_list(request):
    """Список браков с возможностью фильтрации. Агрегирует по заказу."""
    try:
        from apps.orders.models import OrderDefect
        from django.db.models import Sum, Min, Max
        
        qs = OrderDefect.objects.select_related('order', 'workshop', 'rework_task').all()
        
        # Фильтрация по статусу
        status_filter = request.GET.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        
        # Фильтрация по цеху
        workshop_filter = request.GET.get('workshop')
        if workshop_filter:
            qs = qs.filter(workshop_id=workshop_filter)
        
        # Фильтрация по заказу
        order_filter = request.GET.get('order')
        if order_filter:
            qs = qs.filter(order_id=order_filter)
        
        # Агрегируем браки по заказу и статусу pending_review
        aggregated = (
            qs.values('order_id', 'order__name')
              .filter(status='pending_review')
              .annotate(
                  total_quantity=Sum('quantity'),
                  first_date=Min('date'),
                  last_date=Max('date')
              )
              .order_by('-last_date')
        )
        
        # Неагрегированные (не pending) возвращаем как есть
        others = qs.exclude(status='pending_review')
        
        defects_data = []
        for item in aggregated:
            defects_data.append({
                'id': None,
                'order': {
                    'id': item['order_id'],
                    'name': item['order__name']
                },
                'workshop': None,
                'quantity': item['total_quantity'],
                'status': 'pending_review',
                'status_display': 'Ожидает проверки',
                'date': item['last_date'].isoformat() if item['last_date'] else None,
                'comment': f"Агрегировано. Период: {item['first_date']} - {item['last_date']}",
                'admin_comment': '',
                'rework_deadline': None,
                'rework_cost': '0.00',
                'can_be_reworked': True,
                'rework_task': None
            })
        
        for defect in others:
            defects_data.append({
                'id': defect.id,
                'order': {
                    'id': defect.order.id,
                    'name': defect.order.name
                },
                'workshop': {
                    'id': defect.workshop.id,
                    'name': defect.workshop.name
                } if defect.workshop else None,
                'quantity': defect.quantity,
                'status': defect.status,
                'status_display': defect.status_display,
                'date': defect.date.isoformat(),
                'comment': defect.comment,
                'admin_comment': defect.admin_comment,
                'rework_deadline': defect.rework_deadline.isoformat() if defect.rework_deadline else None,
                'rework_cost': str(defect.rework_cost),
                'can_be_reworked': defect.can_be_reworked(),
                'rework_task': defect.rework_task.id if defect.rework_task else None
            })
        
        return Response({
            'defects': defects_data,
            'total': len(defects_data)
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=500) 

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def approve_defects_by_order(request, order_id: int):
    """Разрешить переработку агрегированных браков по заказу: суммирует pending_review и одобряет как один"""
    try:
        from apps.orders.models import OrderDefect, Order
        from django.db.models import Sum

        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return Response({'error': 'Заказ не найден'}, status=404)

        total = OrderDefect.objects.filter(order_id=order_id, status='pending_review').aggregate(s=Sum('quantity'))['s'] or 0
        if total <= 0:
            return Response({'error': 'Нет браков для одобрения'}, status=400)

        # Берем любой цех из браков или первый этап заказа
        workshop = None
        any_defect = OrderDefect.objects.filter(order_id=order_id, status='pending_review').first()
        if any_defect:
            workshop = any_defect.workshop
        if not workshop:
            first_stage = order.stages.order_by('sequence').first()
            if first_stage:
                workshop = first_stage.workshop

        # Создаем одну запись дефекта и одобряем её
        defect = OrderDefect.objects.create(
            order=order,
            workshop=workshop,
            quantity=total,
            comment=f'Агрегированное одобрение браков по заказу #{order.id}'
        )
        # Удаляем исходные pending_review
        OrderDefect.objects.filter(order_id=order_id, status='pending_review').delete()

        comment = request.data.get('comment', '')
        deadline = request.data.get('deadline')
        if deadline:
            from datetime import datetime
            deadline = datetime.strptime(deadline, '%Y-%m-%d').date()

        success, message = defect.approve_for_rework(admin_user=request.user, comment=comment, deadline=deadline)
        if success:
            return Response({'success': True, 'message': message, 'defect_id': defect.id})
        return Response({'success': False, 'error': message}, status=400)
    except Exception as e:
        return Response({'error': str(e)}, status=500) 

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def replenish_defects_by_order(request, order_id: int):
    """Пополнить браки по заказу: перевести pending_review количество в план первого этапа"""
    try:
        from apps.orders.models import Order, OrderDefect
        from django.db.models import Sum
        order = Order.objects.get(id=order_id)
        total = OrderDefect.objects.filter(order_id=order_id, status='pending_review').aggregate(s=Sum('quantity'))['s'] or 0
        if total <= 0:
            return Response({'error': 'Нет браков для пополнения'}, status=400)
        # Увеличиваем план первого этапа
        first_stage = order.stages.order_by('sequence').first()
        if not first_stage:
            return Response({'error': 'Нет этапов в заказе'}, status=400)
        first_stage.plan_quantity = (first_stage.plan_quantity or 0) + total
        note = f"Пополнение браков заказа {order.name} (ID {order.id}) для {order.client}"
        first_stage.operation = f"{first_stage.operation} — {note}" if first_stage.operation else note
        first_stage.save()
        # Удаляем pending браки
        OrderDefect.objects.filter(order_id=order_id, status='pending_review').delete()
        return Response({'success': True, 'added': int(total)})
    except Order.DoesNotExist:
        return Response({'error': 'Сотрудник не найден'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def replenish_defect(request, defect_id: int):
    """Пополнить конкретный дефект: перевести его количество в план первого этапа"""
    try:
        from apps.orders.models import OrderDefect
        defect = OrderDefect.objects.get(id=defect_id)
        order = defect.order
        qty = defect.quantity or 0
        if qty <= 0:
            return Response({'error': 'Количество брака равно 0'}, status=400)
        first_stage = order.stages.order_by('sequence').first()
        if not first_stage:
            return Response({'error': 'Нет этапов в заказе'}, status=400)
        first_stage.plan_quantity = (first_stage.plan_quantity or 0) + qty
        note = f"Пополнение браков заказа {order.name} (ID {order.id}) для {order.client}"
        first_stage.operation = f"{first_stage.operation} — {note}" if first_stage.operation else note
        first_stage.save()
        # Удаляем/переводим дефект в reworked
        defect.status = 'reworked'
        defect.admin_comment = (defect.admin_comment or '') + ' | ' + note
        defect.save()
        return Response({'success': True, 'added': int(qty)})
    except OrderDefect.DoesNotExist:
        return Response({'error': 'Брак не найден'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500) 

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def recalculate_employee_earnings(request, employee_id):
    """Принудительно пересчитывает заработок для сотрудника"""
    try:
        employee = User.objects.get(id=employee_id)
        tasks = EmployeeTask.objects.filter(employee=employee)
        
        updated_count = 0
        total_earnings = 0
        total_penalties = 0
        total_net = 0
        
        for task in tasks:
            try:
                # Сохраняем старые значения
                old_earnings = task.earnings
                old_penalties = task.penalties
                old_net = task.net_earnings
                
                # Пересчитываем заработок
                task.calculate_earnings()
                
                # Обновляем в базе
                EmployeeTask.objects.filter(pk=task.pk).update(
                    earnings=task.earnings,
                    penalties=task.penalties,
                    net_earnings=task.net_earnings
                )
                
                updated_count += 1
                total_earnings += float(task.earnings)
                total_penalties += float(task.penalties)
                total_net += float(task.net_earnings)
                
            except Exception as e:
                print(f"Error recalculating task {task.id}: {e}")
                continue
        
        return Response({
            'success': True,
            'message': f'Пересчитано задач: {updated_count}',
            'updated_count': updated_count,
            'total_earnings': total_earnings,
            'total_penalties': total_penalties,
            'total_net': total_net
        })
        
    except User.DoesNotExist:
        return Response({'error': 'Сотрудник не найден'}, status=404)
    except Exception as e:
        print(f"Error in recalculate_employee_earnings: {e}")
        return Response({'error': str(e)}, status=500) 