from django.db import models
from datetime import datetime, time, timedelta
from django.utils import timezone

# Create your models here.

class Order(models.Model):
    STATUS_CHOICES = [
        ('production', 'В производстве'),
        ('stock', 'На складе'),
        ('shipped', 'Отправлен клиенту'),
        ('new', 'Новая'),
    ]
    name = models.CharField('Название заявки', max_length=200)
    client = models.ForeignKey('clients.Client', on_delete=models.CASCADE, related_name='orders', verbose_name='Клиент')
    workshop = models.ForeignKey('operations_workshops.Workshop', on_delete=models.SET_NULL, null=True, blank=True, related_name='orders', verbose_name='Этап (цех)')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='orders', verbose_name='Продукт', null=True, blank=True)
    quantity = models.PositiveIntegerField('Количество', default=1)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    status = models.CharField('Статус', max_length=30, choices=STATUS_CHOICES, default='production')
    comment = models.CharField('Комментарий', max_length=255, blank=True)
    # Это поле будет вычисляться в будущем (расходы на сырье, услуги, браки)
    expenses = models.FloatField('Расходы', default=0, editable=False)

    class Meta:
        verbose_name = 'Заявка'
        verbose_name_plural = 'Заявки'
        ordering = ['-created_at']

    def __str__(self):
        product_part = f" — {self.product} x{self.quantity}" if self.product else ""
        return f"{self.name} ({self.client}){product_part} [{self.status_display}]"

    @property
    def status_display(self):
        return dict(self.STATUS_CHOICES).get(self.status, self.status)

    @property
    def total_done_count(self):
        return sum(stage.done_count for stage in self.stages.all())

    @property
    def total_defective_count(self):
        return sum(stage.defective_count for stage in self.stages.all())

    @property
    def total_quantity(self):
        items_sum = sum(item.quantity for item in self.items.all())
        return items_sum if items_sum > 0 else (self.quantity or 0)

class OrderStage(models.Model):
    STAGE_TYPE_CHOICES = [
        ('workshop', 'Цех'),
        ('stock', 'Склад готовой продукции'),
    ]
    STAGE_STATUS_CHOICES = [
        ('in_progress', 'В работе'),
        ('done', 'Завершено'),
        ('partial', 'Частично завершено'),
        ('waiting', 'Ожидание'),
    ]
    order = models.ForeignKey('Order', on_delete=models.CASCADE, related_name='stages')
    stage_type = models.CharField('Тип этапа', max_length=20, choices=STAGE_TYPE_CHOICES, default='workshop')
    workshop = models.ForeignKey('operations_workshops.Workshop', on_delete=models.CASCADE, null=True, blank=True)
    finished_good = models.ForeignKey('finished_goods.FinishedGood', on_delete=models.SET_NULL, null=True, blank=True)
    in_progress = models.PositiveIntegerField('В работе', default=0)
    defective = models.PositiveIntegerField('Брак', default=0)
    completed = models.PositiveIntegerField('Передано дальше', default=0)
    date = models.DateTimeField('Дата', auto_now=True)
    comment = models.CharField('Комментарий', max_length=255, blank=True)
    operation = models.CharField('Операция', max_length=100, blank=True)
    sequence = models.PositiveIntegerField('Очередность', default=0)
    plan_quantity = models.PositiveIntegerField('План (кол-во)', default=1)
    completed_quantity = models.PositiveIntegerField('Выполнено (кол-во)', default=0)
    deadline = models.DateField('Срок', null=True, blank=True)
    status = models.CharField('Статус', max_length=30, choices=STAGE_STATUS_CHOICES, default='in_progress')

    class Meta:
        unique_together = ('order', 'workshop', 'stage_type', 'finished_good')
        verbose_name = 'Этап заказа'
        verbose_name_plural = 'Этапы заказа'

    def __str__(self):
        if self.stage_type == 'stock':
            return f"[Склад] {self.order} — {self.finished_good}: {self.in_progress} на складе"
        return f"{self.order} — {self.workshop}: {self.in_progress} в работе, {self.completed} передано, {self.defective} брак"

    @property
    def waiting_for_master(self):
        # Сколько ещё не распределено сотрудникам
        assigned = sum(task.quantity for task in self.employee_tasks.all())
        return max(0, self.plan_quantity - assigned)

    @property
    def in_progress_count(self):
        # Сколько назначено сотрудникам, но не выполнено
        return sum(task.quantity for task in self.employee_tasks.filter(is_completed=False))

    @property
    def done_count(self):
        # Сколько сотрудники уже выполнили (сумма completed_quantity по EmployeeTask)
        return sum(task.completed_quantity for task in self.employee_tasks.all())

    @property
    def defective_count(self):
        # Сумма брака по всем задачам этапа
        return sum(task.defective_quantity for task in self.employee_tasks.all())

    @property
    def transferred_count(self):
        # Сколько мастер перевёл на следующий цех (используем completed)
        return self.completed

    def confirm_stage(self, completed_qty):
        """
        Мастер подтверждает выполнение этапа. Если выполнено не всё — остаток остаётся, выполненное уходит дальше.
        """
        from apps.orders.models import OrderStage
        if completed_qty >= self.plan_quantity:
            self.completed_quantity = self.plan_quantity
            self.status = 'done'
            self.save()
            self._activate_next_stage(self.plan_quantity)
        elif completed_qty > 0:
            # Часть выполнено, часть — остаток
            self.completed_quantity = completed_qty
            self.status = 'partial'
            self.save()
            self._activate_next_stage(completed_qty)
            # Создаём новый этап-остаток в этом же цехе
            OrderStage.objects.create(
                order=self.order,
                stage_type=self.stage_type,
                workshop=self.workshop,
                operation=self.operation,
                sequence=self.sequence,
                plan_quantity=self.plan_quantity - completed_qty,
                completed_quantity=0,
                deadline=None,  # Можно задать новый срок
                status='in_progress',
            )
        else:
            # Ничего не сделано — этап остаётся в работе
            pass

    def _activate_next_stage(self, qty):
        """
        Активирует следующий этап, если он есть, и передаёт туда qty.
        Если следующего этапа нет — создаёт его по workflow.
        """
        from apps.orders.models import OrderStage
        next_seq = self.sequence + 1
        # Найти шаг workflow по sequence
        if next_seq-1 < len(ORDER_WORKFLOW):
            step = ORDER_WORKFLOW[next_seq-1]
            from apps.operations.workshops.models import Workshop
            workshop = Workshop.objects.get(pk=step["workshop"])
            next_stage, created = OrderStage.objects.get_or_create(
                order=self.order,
                sequence=next_seq,
                defaults={
                    'stage_type': 'workshop',
                    'workshop': workshop,
                    'operation': step["operation"],
                    'plan_quantity': qty,
                    'deadline': timezone.now().replace(hour=18, minute=0, second=0, microsecond=0).date(),
                    'status': 'in_progress',
                }
            )
            if not created:
                next_stage.plan_quantity += qty
                next_stage.status = 'in_progress'
                next_stage.save()

class OrderDefect(models.Model):
    DEFECT_STATUS_CHOICES = [
        ('pending_review', 'Ожидает проверки'),
        ('approved_for_rework', 'Разрешена переработка'),
        ('in_rework', 'В переработке'),
        ('reworked', 'Переработан'),
        ('rejected', 'Отклонен'),
    ]
    
    order = models.ForeignKey('Order', on_delete=models.CASCADE, related_name='order_defects')
    workshop = models.ForeignKey('operations_workshops.Workshop', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField('Количество брака', default=1)
    date = models.DateTimeField('Дата', auto_now_add=True)
    comment = models.CharField('Комментарий', max_length=255, blank=True)
    
    # Новые поля для управления браком
    status = models.CharField('Статус брака', max_length=30, choices=DEFECT_STATUS_CHOICES, default='pending_review')
    admin_comment = models.TextField('Комментарий админа', blank=True)
    rework_task = models.ForeignKey('employee_tasks.EmployeeTask', on_delete=models.SET_NULL, null=True, blank=True, related_name='reworked_defects')
    rework_deadline = models.DateField('Срок переработки', null=True, blank=True)
    rework_cost = models.DecimalField('Стоимость переработки', max_digits=10, decimal_places=2, default=0)

    class Meta:
        verbose_name = 'Брак по заказу'
        verbose_name_plural = 'Браки по заказу'
        ordering = ['-date']

    def __str__(self):
        return f"Брак: {self.order} — {self.workshop} ({self.quantity}) [{self.get_status_display()}]"
    
    @property
    def status_display(self):
        return dict(self.DEFECT_STATUS_CHOICES).get(self.status, self.status)
    
    def can_be_reworked(self):
        """Проверяет, можно ли переработать брак"""
        return self.status in ['pending_review', 'approved_for_rework']
    
    def approve_for_rework(self, admin_user, comment='', deadline=None):
        """Админ разрешает переработку брака"""
        if self.status != 'pending_review':
            return False, "Брак уже не в статусе ожидания проверки"
        
        self.status = 'approved_for_rework'
        self.admin_comment = comment
        self.rework_deadline = deadline
        self.save()
        
        # Увеличиваем план первого этапа заказа, чтобы покрыть брак
        try:
            first_stage = self.order.stages.order_by('sequence').first()
            if first_stage:
                first_stage.plan_quantity = (first_stage.plan_quantity or 0) + self.quantity
                # Добавим пометку
                if first_stage.operation:
                    first_stage.operation = f"{first_stage.operation} (покрытие брака заказа #{self.order.id})"
                else:
                    first_stage.operation = f"Покрытие брака заказа #{self.order.id}"
                first_stage.save()
        except Exception:
            pass
        
        # Создаем задачу на переработку
        self._create_rework_task()
        return True, "Брак разрешен к переработке"
    
    def _create_rework_task(self):
        """Создает/обновляет этап для переработки брака (без создания задачи)"""
        # Создаем новый этап для переработки
        rework_stage, created = OrderStage.objects.get_or_create(
            order=self.order,
            workshop=self.workshop,
            stage_type='workshop',
            defaults={
                'operation': f'Переработка брака: {self.comment}',
                'plan_quantity': self.quantity,
                'status': 'in_progress',
                'deadline': self.rework_deadline,
                'sequence': 999  # Высокий приоритет
            }
        )
        
        if not created:
            rework_stage.plan_quantity = (rework_stage.plan_quantity or 0) + self.quantity
            rework_stage.save()
        
        # Привязку задачи создадим позже, когда будет назначен сотрудник
        return rework_stage
    
    def start_rework(self, employee):
        """Начинает переработку брака"""
        if self.status != 'approved_for_rework':
            return False, "Брак не разрешен к переработке"
        
        # Гарантируем наличие этапа
        rework_stage = self._create_rework_task()
        
        # Создаем задачу для переработки при первом старте
        if not self.rework_task:
            from apps.employee_tasks.models import EmployeeTask
            rework_task = EmployeeTask.objects.create(
                stage=rework_stage,
                employee=employee,
                quantity=self.quantity,
                completed_quantity=0,
                defective_quantity=0
            )
            self.rework_task = rework_task
        else:
            # Если задача уже есть — назначим сотрудника, если пуст
            self.rework_task.employee = employee
            self.rework_task.save()
        
        self.status = 'in_rework'
        self.save()
        
        return True, "Переработка начата"
    
    def complete_rework(self, completed_quantity, defective_quantity=0):
        """Завершает переработку брака"""
        if self.status != 'in_rework':
            return False, "Брак не в процессе переработки"
        
        if not self.rework_task:
            return False, "Задача на переработку не найдена"
        
        # Обновляем задачу
        self.rework_task.completed_quantity = completed_quantity
        self.rework_task.defective_quantity = defective_quantity
        self.rework_task.save()
        
        # Если переработка успешна
        if completed_quantity > 0 and defective_quantity == 0:
            self.status = 'reworked'
            self.rework_cost = self.rework_task.net_earnings
        else:
            # Если снова брак, возвращаем в ожидание
            self.status = 'pending_review'
        
        self.save()
        return True, "Переработка завершена"
    
    def reject_defect(self, admin_user, comment=''):
        """Админ отклоняет брак (списывает в убытки)"""
        if self.status != 'pending_review':
            return False, "Брак уже не в статусе ожидания проверки"
        
        self.status = 'rejected'
        self.admin_comment = comment
        self.save()
        
        return True, "Брак отклонен"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items', verbose_name='Заявка')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='order_items', verbose_name='Товар')
    quantity = models.PositiveIntegerField('Количество', default=1)
    size = models.CharField('Размер', max_length=100, blank=True)
    color = models.CharField('Цвет', max_length=100, blank=True)

    class Meta:
        verbose_name = 'Позиция заявки'
        verbose_name_plural = 'Позиции заявки'

    def __str__(self):
        details = []
        if self.size:
            details.append(self.size)
        if self.color:
            details.append(self.color)
        suffix = f" ({', '.join(details)})" if details else ''
        return f"{self.product} x{self.quantity}{suffix}"

ORDER_WORKFLOW = [
    {"workshop": 1, "operation": "Резка"},
    {"workshop": 2, "operation": "ЧПУ"},
    {"workshop": 3, "operation": "Заготовка досок"},
    {"workshop": 4, "operation": "Пресс"},
    {"workshop": 1, "operation": "Распил (места)"},
    {"workshop": 5, "operation": "Кромка"},
    {"workshop": 6, "operation": "Шкурка аппаратная"},
    {"workshop": 7, "operation": "Шкурка сухой"},
    {"workshop": 8, "operation": "Шкурка ручная"},
    {"workshop": 9, "operation": "Грунтовка"},
    {"workshop": 10, "operation": "Шкурка белый"},
    {"workshop": 11, "operation": "Покраска"},
    {"workshop": 12, "operation": "Упаковка"},
]

def create_order_stages(order):
    from apps.operations.workshops.models import Workshop
    # Создаём только первый этап из workflow
    if not ORDER_WORKFLOW:
        return
    step = ORDER_WORKFLOW[0]
    workshop = Workshop.objects.get(pk=step["workshop"])
    # deadline = сегодня 18:00
    now = timezone.now()
    deadline_dt = now.replace(hour=18, minute=0, second=0, microsecond=0)
    if now.hour >= 18:
        # если заказ создан после 18:00, дедлайн на следующий день
        deadline_dt += timedelta(days=1)
    OrderStage.objects.create(
        order=order,
        workshop=workshop,
        operation=step["operation"],
        sequence=1,
        stage_type='workshop',
        plan_quantity=order.total_quantity,
        deadline=deadline_dt.date(),
        status='in_progress',
    )

from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Order)
def create_stages_on_order(sender, instance, created, **kwargs):
    if created and not instance.stages.exists():
        # Создаем этапы только если уже есть позиции или задан одиночный продукт
        if instance.items.exists() or (instance.product_id and instance.quantity > 0):
            create_order_stages(instance)
