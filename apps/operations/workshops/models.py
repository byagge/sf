from django.db import models

class Workshop(models.Model):
    name = models.CharField('Название цеха', max_length=100)
    manager = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='operation_managed_workshops',
        limit_choices_to={'role': 'master'},
        verbose_name='Руководитель (мастер)'
    )
    description = models.TextField('Описание', blank=True)
    is_active = models.BooleanField('Активен', default=True)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)

    class Meta:
        verbose_name = 'Цех'
        verbose_name_plural = 'Цеха'

    def __str__(self):
        return self.name

    def set_manager(self, user):
        """
        Назначает пользователя руководителем цеха и автоматически изменяет его роль на 'master'
        """
        from apps.users.models import User
        
        # Если был предыдущий руководитель, возвращаем ему роль 'worker'
        if self.manager and self.manager != user:
            # Проверяем, не является ли он руководителем других цехов
            other_workshops = Workshop.objects.filter(manager=self.manager).exclude(pk=self.pk)
            if not other_workshops.exists():
                self.manager.role = User.Role.WORKER
                self.manager.save()
        
        # Назначаем нового руководителя
        self.manager = user
        
        # Изменяем роль нового руководителя на 'master'
        if user and user.role != User.Role.MASTER:
            user.role = User.Role.MASTER
            user.save()
        
        # Сохраняем цех
        self.save()

    def get_orders_info(self):
        """
        Возвращает информацию о заказах в цехе с полной информацией о товарах
        """
        from apps.orders.models import OrderStage
        from apps.employee_tasks.models import EmployeeTask
        
        # Получаем все активные этапы в цехе
        stages = OrderStage.objects.filter(
            workshop=self,
            status__in=['in_progress', 'partial']
        ).select_related(
            'order', 'order_item', 'order_item__product'
        ).prefetch_related(
            'employee_tasks'
        )
        
        orders_info = []
        
        for stage in stages:
            if not stage.order_item:
                continue
                
            # Получаем задачи сотрудников для этого этапа
            employee_tasks = EmployeeTask.objects.filter(stage=stage).select_related('employee')
            
            # Подсчитываем статистику
            total_assigned = sum(task.quantity for task in employee_tasks)
            total_completed = sum(task.completed_quantity for task in employee_tasks)
            total_defective = sum(task.defective_quantity for task in employee_tasks)
            
            # Получаем информацию о товаре
            product_info = {
                'id': stage.order_item.product.id if stage.order_item.product else None,
                'name': stage.order_item.product.name if stage.order_item.product else 'Не указан',
                'is_glass': stage.order_item.product.is_glass if stage.order_item.product else False,
                'glass_type': stage.order_item.glass_type,
                'glass_type_display': stage.order_item.get_glass_type_display(),
                'img': stage.order_item.product.img.url if stage.order_item.product and stage.order_item.product.img else None,
                'size': stage.order_item.size,
                'color': stage.order_item.color,
                'paint_type': stage.order_item.paint_type,
                'paint_color': stage.order_item.paint_color,
                'cnc_specs': stage.order_item.cnc_specs,
                'cutting_specs': stage.order_item.cutting_specs,
                'packaging_notes': stage.order_item.packaging_notes,
            }
            
            # Информация о заказе
            order_info = {
                'id': stage.order.id,
                'name': stage.order.name,
                'status': stage.order.status,
                'status_display': stage.order.get_status_display(),
                'client_name': stage.order.client.name if stage.order.client else 'Не указан',
            }
            
            # Информация об этапе
            stage_info = {
                'id': stage.id,
                'operation': stage.operation,
                'plan_quantity': stage.plan_quantity,
                'completed_quantity': stage.completed_quantity,
                'status': stage.status,
                'deadline': stage.deadline.isoformat() if stage.deadline else None,
                'parallel_group': stage.parallel_group,
            }
            
            # Информация о задачах сотрудников
            tasks_info = []
            for task in employee_tasks:
                tasks_info.append({
                    'id': task.id,
                    'employee_name': task.employee.get_full_name() if hasattr(task.employee, 'get_full_name') else f"{task.employee.first_name} {task.employee.last_name}".strip(),
                    'quantity': task.quantity,
                    'completed_quantity': task.completed_quantity,
                    'defective_quantity': task.defective_quantity,
                    'is_completed': task.is_completed,
                })
            
            orders_info.append({
                'stage': stage_info,
                'order': order_info,
                'product': product_info,
                'tasks': tasks_info,
                'statistics': {
                    'total_assigned': total_assigned,
                    'total_completed': total_completed,
                    'total_defective': total_defective,
                    'remaining': stage.plan_quantity - total_completed,
                    'progress_percent': (total_completed / stage.plan_quantity * 100) if stage.plan_quantity > 0 else 0,
                }
            })
        
        return orders_info

    def get_workshop_summary(self):
        """
        Возвращает сводную информацию о цехе
        """
        from apps.orders.models import OrderStage
        from apps.employee_tasks.models import EmployeeTask
        from django.db.models import F
        
        # Общая статистика
        total_stages = OrderStage.objects.filter(workshop=self, status__in=['in_progress', 'partial']).count()
        total_tasks = EmployeeTask.objects.filter(stage__workshop=self).count()
        total_completed_tasks = EmployeeTask.objects.filter(stage__workshop=self, completed_quantity__gte=F('quantity')).count()
        
        # Статистика по заказам
        active_orders = OrderStage.objects.filter(
            workshop=self,
            status__in=['in_progress', 'partial']
        ).values('order').distinct().count()
        
        return {
            'workshop_name': self.name,
            'manager_name': self.manager.get_full_name() if self.manager else 'Не назначен',
            'total_stages': total_stages,
            'total_tasks': total_tasks,
            'completed_tasks': total_completed_tasks,
            'active_orders': active_orders,
            'completion_rate': (total_completed_tasks / total_tasks * 100) if total_tasks > 0 else 0,
        }
