from django.db import models
from apps.products.models import Product
from apps.users.models import User
from apps.operations.workshops.models import Workshop

class Defect(models.Model):
    class DefectType(models.TextChoices):
        TECHNICAL = 'technical', 'Технический'
        MANUAL = 'manual', 'Ручной'
    
    class DefectStatus(models.TextChoices):
        PENDING = 'pending', 'Ожидает подтверждения мастера'
        CONFIRMED = 'confirmed', 'Подтвержден мастером'
        REPAIRABLE = 'repairable', 'Можно починить'
        IRREPARABLE = 'irreparable', 'Нельзя починить'
        TRANSFERRED = 'transferred', 'Переведен в другой цех'
        REPAIRED = 'repaired', 'Починен'
        CLOSED = 'closed', 'Закрыт'
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='defects', verbose_name='Продукт')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='defects', verbose_name='Сотрудник (кто создал брак)')
    created_at = models.DateTimeField('Дата брака', auto_now_add=True)
    
    # Новые поля для системы подтверждения
    status = models.CharField(
        max_length=20,
        choices=DefectStatus.choices,
        default=DefectStatus.PENDING,
        verbose_name='Статус брака'
    )
    defect_type = models.CharField(
        max_length=20,
        choices=DefectType.choices,
        null=True,
        blank=True,
        verbose_name='Тип брака'
    )
    
    # Поля для подтверждения мастером
    confirmed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='confirmed_defects',
        verbose_name='Мастер, подтвердивший брак',
        limit_choices_to={'role': 'master'}
    )
    confirmed_at = models.DateTimeField('Дата подтверждения', null=True, blank=True)
    
    # Поля для перевода в другой цех
    target_workshop = models.ForeignKey(
        Workshop,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='incoming_defects',
        verbose_name='Цех для исправления'
    )
    transferred_at = models.DateTimeField('Дата перевода', null=True, blank=True)
    
    # Поля для починки
    is_repairable = models.BooleanField('Можно починить', null=True, blank=True)
    repair_task = models.ForeignKey(
        'employee_tasks.EmployeeTask',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='defect_repair_tasks',
        verbose_name='Задача на починку'
    )
    
    # Комментарии
    master_comment = models.TextField('Комментарий мастера', blank=True)
    repair_comment = models.TextField('Комментарий по починке', blank=True)
    
    # Штрафные санкции
    penalty_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Сумма штрафа',
    )
    penalty_applied = models.BooleanField('Штраф применен', default=False)

    def __str__(self):
        return f"Брак: {self.product} ({self.user}) - {self.get_status_display()}"

    def get_workshop(self):
        """Возвращает цех, в котором работает сотрудник, создавший брак"""
        return self.user.workshop if self.user else None
    
    def can_be_confirmed_by(self, user):
        """Проверяет, может ли пользователь подтвердить этот брак"""
        if user.role != User.Role.MASTER:
            return False
        
        # Мастер должен быть привязан к какому-либо цеху
        if not user.workshop_id:
            return False
        
        # Разрешаем, если брак создан сотрудником из цеха мастера
        defect_workshop = self.get_workshop()
        if defect_workshop and defect_workshop.id == user.workshop_id:
            return True
        
        # Также разрешаем, если целевой цех брака совпадает с цехом мастера
        if self.target_workshop_id and self.target_workshop_id == user.workshop_id:
            return True
        
        return False
    
    def confirm_defect(self, master, is_repairable, defect_type=None, target_workshop=None, comment=''):
        """Подтверждает брак мастером"""
        from django.utils import timezone
        
        if not self.can_be_confirmed_by(master):
            raise ValueError("Мастер не может подтвердить этот брак")
        
        self.confirmed_by = master
        self.confirmed_at = timezone.now()
        self.is_repairable = is_repairable
        self.master_comment = comment
        
        # Базовый статус подтверждения
        self.status = self.DefectStatus.CONFIRMED
        
        if is_repairable:
            # Если можно починить — переводим в REPAIRABLE без создания этапов/задач
            self.status = self.DefectStatus.REPAIRABLE
        else:
            # Если нельзя починить — ставим статус IRREPARABLE и тип брака
            self.status = self.DefectStatus.IRREPARABLE
            self.defect_type = defect_type
            # Применяем штраф для ручного брака
            if defect_type == self.DefectType.MANUAL:
                self._apply_penalty()
            # Если указан целевой цех — переводим брак (без создания этапов/задач)
            if target_workshop:
                self._transfer_to_workshop(target_workshop)
        
        self.save()
    
    def _create_repair_task(self):
        """Создает задачу на починку брака"""
        from apps.employee_tasks.models import EmployeeTask
        from apps.orders.models import OrderStage
        
        # Создаем фиктивный этап заказа для починки брака
        if not hasattr(self, '_repair_stage'):
            self._repair_stage = OrderStage.objects.create(
                order=None,  # Брак не привязан к конкретному заказу
                workshop=self.get_workshop(),
                service=None,  # Услуга будет определена позже
                quantity=1,
                completed_quantity=0,
                status='in_progress'
            )
        
        # Создаем задачу для сотрудника
        repair_task = EmployeeTask.objects.create(
            stage=self._repair_stage,
            employee=self.user,
            quantity=1,
            completed_quantity=0
        )
        
        self.repair_task = repair_task
        self.save()
    
    def _apply_penalty(self):
        """Применяет штраф за ручной брак"""
        if self.user and self.user.workshop:
            from apps.services.models import Service
            try:
                service = Service.objects.filter(workshop=self.user.workshop, is_active=True).first()
                if service and hasattr(service, 'defect_penalty'):
                    self.penalty_amount = service.defect_penalty
                    self.penalty_applied = True
            except:
                pass
    
    def _transfer_to_workshop(self, target_workshop):
        """Переводит брак в другой цех для исправления (без создания этапов/задач)"""
        from django.utils import timezone
        
        self.target_workshop = target_workshop
        self.transferred_at = timezone.now()
        self.status = self.DefectStatus.TRANSFERRED
        # Не создаем никаких OrderStage/EmployeeTask, чтобы соответствовать текущей схеме
        self.save()
    
    def _create_transfer_task(self, target_workshop):
        """Создает задачу для мастера целевого цеха"""
        from apps.employee_tasks.models import EmployeeTask
        from apps.orders.models import OrderStage
        
        # Создаем этап для восстановления брака
        recovery_stage = OrderStage.objects.create(
            order=None,
            workshop=target_workshop,
            service=None,
            quantity=1,
            completed_quantity=0,
            status='in_progress'
        )
        
        # Создаем задачу для мастера
        recovery_task = EmployeeTask.objects.create(
            stage=recovery_stage,
            employee=target_workshop.manager,
            quantity=1,
            completed_quantity=0
        )
        
        # Обновляем связь с задачей восстановления
        self.repair_task = recovery_task
        self.save()
    
    def mark_as_repaired(self, comment=''):
        """Отмечает брак как починенный"""
        from django.utils import timezone
        
        self.status = self.DefectStatus.REPAIRED
        self.repair_comment = comment
        self.completed_at = timezone.now()
        self.save()
    
    def close_defect(self):
        """Закрывает брак"""
        self.status = self.DefectStatus.CLOSED
        self.save()

    class Meta:
        verbose_name = 'Брак'
        verbose_name_plural = 'Браки'
        ordering = ['-created_at'] 