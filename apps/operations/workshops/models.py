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
        verbose_name='Главный руководитель (мастер)'
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

    def get_all_masters(self):
        """
        Возвращает всех мастеров цеха (главный + дополнительные)
        """
        masters = []
        if self.manager:
            masters.append(self.manager)
        
        additional_masters = self.workshop_masters.filter(is_active=True).select_related('master')
        masters.extend([wm.master for wm in additional_masters])
        
        return masters

    def get_master_names(self):
        """
        Возвращает список имен всех мастеров цеха
        """
        masters = self.get_all_masters()
        return [master.get_full_name() for master in masters]

    def set_manager(self, user):
        """
        Назначает пользователя главным руководителем цеха и автоматически изменяет его роль на 'master'
        """
        from apps.users.models import User
        
        # Если был предыдущий руководитель, возвращаем ему роль 'worker'
        if self.manager and self.manager != user:
            # Проверяем, не является ли он руководителем других цехов
            other_workshops = Workshop.objects.filter(manager=self.manager).exclude(pk=self.pk)
            other_workshop_masters = WorkshopMaster.objects.filter(master=self.manager, is_active=True).exclude(workshop=self)
            if not other_workshops.exists() and not other_workshop_masters.exists():
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

    def add_master(self, user):
        """
        Добавляет дополнительного мастера к цеху
        """
        from apps.users.models import User
        
        # Проверяем, не является ли пользователь уже главным мастером
        if self.manager == user:
            return False, "Пользователь уже является главным мастером цеха"
        
        # Проверяем, не является ли пользователь уже дополнительным мастером
        if self.workshop_masters.filter(master=user, is_active=True).exists():
            return False, "Пользователь уже является дополнительным мастером цеха"
        
        # Изменяем роль пользователя на 'master'
        if user.role != User.Role.MASTER:
            user.role = User.Role.MASTER
            user.save()
        
        # Создаем связь
        WorkshopMaster.objects.create(
            workshop=self,
            master=user,
            is_active=True
        )
        
        return True, "Мастер успешно добавлен к цеху"

    def remove_master(self, user):
        """
        Удаляет дополнительного мастера из цеха
        """
        # Нельзя удалить главного мастера через этот метод
        if self.manager == user:
            return False, "Нельзя удалить главного мастера цеха"
        
        # Удаляем связь
        workshop_master = self.workshop_masters.filter(master=user, is_active=True).first()
        if workshop_master:
            workshop_master.is_active = False
            workshop_master.save()
            
            # Проверяем, не является ли пользователь мастером других цехов
            other_workshops = Workshop.objects.filter(manager=user)
            other_workshop_masters = WorkshopMaster.objects.filter(master=user, is_active=True)
            if not other_workshops.exists() and not other_workshop_masters.exists():
                # Возвращаем роль 'worker'
                from apps.users.models import User
                user.role = User.Role.WORKER
                user.save()
            
            return True, "Мастер успешно удален из цеха"
        
        return False, "Пользователь не найден среди мастеров цеха"

    def is_user_master(self, user):
        """
        Проверяет, является ли пользователь мастером цеха (главным или дополнительным)
        """
        if not user:
            return False
        
        # Проверяем главного мастера
        if self.manager == user:
            return True
        
        # Проверяем дополнительных мастеров
        return self.workshop_masters.filter(master=user, is_active=True).exists()

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
        
        # Получаем всех мастеров
        all_masters = self.get_all_masters()
        master_names = [master.get_full_name() for master in all_masters]
        
        return {
            'workshop_name': self.name,
            'manager_name': self.manager.get_full_name() if self.manager else 'Не назначен',
            'all_masters': master_names,
            'total_stages': total_stages,
            'total_tasks': total_tasks,
            'completed_tasks': total_completed_tasks,
            'active_orders': active_orders,
            'completion_rate': (total_completed_tasks / total_tasks * 100) if total_tasks > 0 else 0,
        }

    @classmethod
    def get_master_statistics(cls, master_user):
        """
        Возвращает статистику по всем цехам мастера
        """
        from apps.orders.models import OrderStage
        from apps.employee_tasks.models import EmployeeTask
        from apps.defects.models import Defect
        from django.db.models import Q, Count, Sum, Avg
        from django.utils import timezone
        from datetime import timedelta
        
        # Получаем все цеха мастера
        managed_workshops = cls.objects.filter(
            Q(manager=master_user) | Q(workshop_masters__master=master_user, workshop_masters__is_active=True)
        ).distinct()
        
        if not managed_workshops.exists():
            return None
        
        # Текущие даты для фильтрации
        now = timezone.now()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        
        # Общая статистика по всем цехам мастера
        total_workshops = managed_workshops.count()
        
        # Статистика по задачам
        all_tasks = EmployeeTask.objects.filter(stage__workshop__in=managed_workshops)
        total_tasks = all_tasks.count()
        completed_tasks = all_tasks.filter(completed_quantity__gte=models.F('quantity')).count()
        
        # Статистика по этапам
        all_stages = OrderStage.objects.filter(workshop__in=managed_workshops)
        total_stages = all_stages.count()
        active_stages = all_stages.filter(status__in=['in_progress', 'partial']).count()
        completed_stages = all_stages.filter(status='completed').count()
        
        # Статистика по браку
        total_defects = Defect.objects.filter(
            user__workshop__in=managed_workshops
        ).count()
        
        # Статистика за неделю
        week_tasks = all_tasks.filter(created_at__gte=week_ago)
        week_completed = week_tasks.filter(completed_quantity__gte=F('quantity')).count()
        week_defects = Defect.objects.filter(
            user__workshop__in=managed_workshops,
            created_at__gte=week_ago
        ).count()
        
        # Статистика за месяц
        month_tasks = all_tasks.filter(created_at__gte=month_ago)
        month_completed = month_tasks.filter(completed_quantity__gte=F('quantity')).count()
        month_defects = Defect.objects.filter(
            user__workshop__in=managed_workshops,
            created_at__gte=month_ago
        ).count()
        
        # Эффективность
        efficiency = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        week_efficiency = (week_completed / week_tasks.count() * 100) if week_tasks.count() > 0 else 0
        month_efficiency = (month_completed / month_tasks.count() * 100) if month_tasks.count() > 0 else 0
        
        # Статистика по каждому цеху
        workshops_stats = []
        for workshop in managed_workshops:
            workshop_tasks = EmployeeTask.objects.filter(stage__workshop=workshop)
            workshop_completed = workshop_tasks.filter(completed_quantity__gte=F('quantity')).count()
            workshop_defects = Defect.objects.filter(user__workshop=workshop).count()
            workshop_efficiency = (workshop_completed / workshop_tasks.count() * 100) if workshop_tasks.count() > 0 else 0
            
            workshops_stats.append({
                'id': workshop.id,
                'name': workshop.name,
                'description': workshop.description,
                'total_tasks': workshop_tasks.count(),
                'completed_tasks': workshop_completed,
                'defects': workshop_defects,
                'efficiency': workshop_efficiency,
                'active_stages': OrderStage.objects.filter(
                    workshop=workshop, 
                    status__in=['in_progress', 'partial']
                ).count(),
                'employees_count': workshop.users.count() if hasattr(workshop, 'users') else 0,
            })
        
        return {
            'master_info': {
                'id': master_user.id,
                'name': master_user.get_full_name(),
                'email': master_user.email,
            },
            'overall_stats': {
                'total_workshops': total_workshops,
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks,
                'total_stages': total_stages,
                'active_stages': active_stages,
                'completed_stages': completed_stages,
                'total_defects': total_defects,
                'efficiency': efficiency,
            },
            'period_stats': {
                'week': {
                    'completed_tasks': week_completed,
                    'defects': week_defects,
                    'efficiency': week_efficiency,
                },
                'month': {
                    'completed_tasks': month_completed,
                    'defects': month_defects,
                    'efficiency': month_efficiency,
                }
            },
            'workshops': workshops_stats,
        }


class WorkshopMaster(models.Model):
    """
    Модель для связи мастеров с цехами (многие ко многим)
    """
    workshop = models.ForeignKey(
        Workshop,
        on_delete=models.CASCADE,
        related_name='workshop_masters',
        verbose_name='Цех'
    )
    master = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='workshop_master_roles',
        limit_choices_to={'role': 'master'},
        verbose_name='Мастер'
    )
    is_active = models.BooleanField('Активен', default=True)
    added_at = models.DateTimeField('Дата назначения', auto_now_add=True)
    added_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='added_workshop_masters',
        verbose_name='Назначил'
    )
    notes = models.TextField('Примечания', blank=True)

    class Meta:
        verbose_name = 'Мастер цеха'
        verbose_name_plural = 'Мастера цехов'
        unique_together = ['workshop', 'master']
        ordering = ['-added_at']

    def __str__(self):
        return f"{self.master.get_full_name()} - {self.workshop.name}"

    def save(self, *args, **kwargs):
        """
        Автоматически устанавливаем роль 'master' при создании связи
        """
        if not self.pk:  # Только при создании
            if self.master.role != 'master':
                self.master.role = 'master'
                self.master.save()
        super().save(*args, **kwargs)
