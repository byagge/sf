from django.db import models
from apps.products.models import Product
from apps.users.models import User
from apps.operations.workshops.models import Workshop

class Defect(models.Model):
    class DefectType(models.TextChoices):
        TECHNICAL = 'technical', 'Технический'
        MANUAL = 'manual', 'Ручной'
    
    class DefectStatus(models.TextChoices):
        PENDING_MASTER_REVIEW = 'pending_master_review', 'Ожидает проверки мастера'
        MASTER_CONFIRMED = 'master_confirmed', 'Подтвержден мастером'
        CAN_BE_FIXED = 'can_be_fixed', 'Можно починить'
        SENT_TO_WORKSHOP = 'sent_to_workshop', 'Отправлен в цех для восстановления'
        FIXED = 'fixed', 'Исправлен'
        UNREPAIRABLE = 'unrepairable', 'Не подлежит восстановлению'
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='defects', verbose_name='Продукт')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='defects', verbose_name='Сотрудник (кто создал брак)')
    created_at = models.DateTimeField('Дата брака', auto_now_add=True)
    
    # Новые поля для улучшенной системы
    status = models.CharField(
        max_length=30,
        choices=DefectStatus.choices,
        default=DefectStatus.PENDING_MASTER_REVIEW,
        verbose_name='Статус брака'
    )
    defect_type = models.CharField(
        max_length=20,
        choices=DefectType.choices,
        null=True,
        blank=True,
        verbose_name='Тип брака'
    )
    can_be_fixed = models.BooleanField(
        null=True,
        blank=True,
        verbose_name='Можно ли починить'
    )
    target_workshop = models.ForeignKey(
        Workshop,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='defects_to_fix',
        verbose_name='Цех для восстановления'
    )
    master_confirmed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Дата подтверждения мастером'
    )
    master_confirmed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='confirmed_defects',
        verbose_name='Мастер, подтвердивший брак'
    )
    fixed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Дата исправления'
    )
    fixed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fixed_defects',
        verbose_name='Сотрудник, исправивший брак'
    )
    notes = models.TextField('Примечания', blank=True)

    def __str__(self):
        return f"Брак: {self.product} ({self.user}) - {self.get_status_display()}"

    def get_workshop(self):
        """Возвращает цех, в котором работает сотрудник, создавший брак"""
        return self.user.workshop if self.user else None 
    
    def get_master_workshop(self):
        """Возвращает цех, мастер которого должен проверить брак"""
        return self.get_workshop()
    
    def can_master_review(self, user):
        """Проверяет, может ли пользователь (мастер) проверить этот брак"""
        if user.role != User.Role.MASTER:
            return False
        return user.workshop == self.get_workshop()
    
    def confirm_by_master(self, master_user):
        """Подтверждает брак мастером"""
        if not self.can_master_review(master_user):
            raise ValueError("Пользователь не может подтвердить этот брак")
        
        self.status = self.DefectStatus.MASTER_CONFIRMED
        self.master_confirmed_by = master_user
        self.master_confirmed_at = models.timezone.now()
        self.save()
    
    def set_repairability(self, can_be_fixed):
        """Устанавливает, можно ли починить брак"""
        self.can_be_fixed = can_be_fixed
        if can_be_fixed:
            self.status = self.DefectStatus.CAN_BE_FIXED
        else:
            self.status = self.DefectStatus.UNREPAIRABLE
        self.save()
    
    def set_defect_type(self, defect_type):
        """Устанавливает тип брака"""
        self.defect_type = defect_type
        self.save()
    
    def send_to_workshop(self, workshop):
        """Отправляет брак в цех для восстановления"""
        self.target_workshop = workshop
        self.status = self.DefectStatus.SENT_TO_WORKSHOP
        self.save()
    
    def mark_as_fixed(self, fixed_by_user):
        """Отмечает брак как исправленный"""
        self.status = self.DefectStatus.FIXED
        self.fixed_by = fixed_by_user
        self.fixed_at = models.timezone.now()
        self.save()

    class Meta:
        verbose_name = 'Брак'
        verbose_name_plural = 'Браки'
        ordering = ['-created_at']


class DefectRepairTask(models.Model):
    """Задача по восстановлению брака"""
    class TaskStatus(models.TextChoices):
        PENDING = 'pending', 'Ожидает выполнения'
        IN_PROGRESS = 'in_progress', 'В работе'
        COMPLETED = 'completed', 'Завершена'
        CANCELLED = 'cancelled', 'Отменена'
    
    defect = models.OneToOneField(
        Defect,
        on_delete=models.CASCADE,
        related_name='repair_task',
        verbose_name='Брак'
    )
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='defect_repair_tasks',
        verbose_name='Назначено на'
    )
    workshop = models.ForeignKey(
        Workshop,
        on_delete=models.CASCADE,
        related_name='defect_repair_tasks',
        verbose_name='Цех'
    )
    status = models.CharField(
        max_length=20,
        choices=TaskStatus.choices,
        default=TaskStatus.PENDING,
        verbose_name='Статус задачи'
    )
    title = models.CharField(
        max_length=200,
        verbose_name='Название задачи'
    )
    description = models.TextField(
        verbose_name='Описание задачи',
        blank=True
    )
    priority = models.CharField(
        max_length=20,
        choices=[
            ('low', 'Низкий'),
            ('medium', 'Средний'),
            ('high', 'Высокий'),
            ('urgent', 'Срочно')
        ],
        default='medium',
        verbose_name='Приоритет'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Дата начала работы'
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Дата завершения'
    )
    estimated_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Оценка времени (часы)'
    )
    actual_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Фактическое время (часы)'
    )
    notes = models.TextField(
        verbose_name='Примечания',
        blank=True
    )

    def __str__(self):
        return f"Восстановление брака: {self.defect.product} (Заказ {self.defect.product.order.id if hasattr(self.defect.product, 'order') else 'N/A'})"

    def save(self, *args, **kwargs):
        """Автоматически генерируем название задачи при создании"""
        if not self.pk and not self.title:
            order_id = getattr(self.defect.product, 'order', None)
            if order_id:
                self.title = f"Восстановление брака по заказу {order_id}"
            else:
                self.title = f"Восстановление брака {self.defect.product.name}"
        super().save(*args, **kwargs)

    def assign_to_employee(self, employee):
        """Назначает задачу сотруднику"""
        self.assigned_to = employee
        self.status = self.TaskStatus.PENDING
        self.save()

    def start_work(self):
        """Начинает работу над задачей"""
        self.status = self.TaskStatus.IN_PROGRESS
        self.started_at = models.timezone.now()
        self.save()

    def complete_task(self):
        """Завершает задачу"""
        self.status = self.TaskStatus.COMPLETED
        self.completed_at = models.timezone.now()
        self.save()
        # Отмечаем брак как исправленный
        if self.assigned_to:
            self.defect.mark_as_fixed(self.assigned_to)

    class Meta:
        verbose_name = 'Задача по восстановлению брака'
        verbose_name_plural = 'Задачи по восстановлению браков'
        ordering = ['-created_at'] 