from django.db import models
from apps.orders.models import OrderStage
from django.contrib.auth import get_user_model
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.db import transaction
from decimal import Decimal

User = get_user_model()

class EmployeeTask(models.Model):
    stage = models.ForeignKey(OrderStage, on_delete=models.CASCADE, related_name='employee_tasks')
    employee = models.ForeignKey(User, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    completed_quantity = models.PositiveIntegerField(default=0)
    defective_quantity = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Новые поля для заработка и штрафов
    earnings = models.DecimalField('Заработок', max_digits=10, decimal_places=2, default=0)
    penalties = models.DecimalField('Штрафы', max_digits=10, decimal_places=2, default=0)
    net_earnings = models.DecimalField('Чистый заработок', max_digits=10, decimal_places=2, default=0)
    
    # Связь с услугой через цех
    @property
    def service(self):
        """Получаем услугу через цех этапа"""
        if self.stage.workshop:
            from apps.services.models import Service
            try:
                # Получаем первую активную услугу для цеха
                return Service.objects.filter(workshop=self.stage.workshop, is_active=True).first()
            except Service.DoesNotExist:
                return None
        return None

    class Meta:
        verbose_name = 'Задача сотрудника'
        verbose_name_plural = 'Задачи сотрудников'

    def __str__(self):
        return f"Задача {self.employee} - {self.stage}"

    def calculate_earnings(self):
        """Рассчитывает заработок, штрафы и чистый заработок"""
        if not self.service:
            # Если услуга не найдена, устанавливаем нулевые значения
            self.earnings = Decimal('0.00')
            self.penalties = Decimal('0.00')
            self.net_earnings = Decimal('0.00')
            return
        
        # Заработок за выполненную работу
        self.earnings = Decimal(str(self.completed_quantity)) * self.service.service_price
        
        # Штрафы теперь начисляются только после подтверждения мастером
        # Здесь оставляем только уже примененные штрафы (из системы браков)
        # self.penalties остается как есть - обновляется только при подтверждении брака мастером
        
        # Чистый заработок
        self.net_earnings = self.earnings - self.penalties

    @property
    def is_completed(self):
        """Проверяет, выполнена ли задача полностью"""
        return self.completed_quantity >= self.quantity
    
    @property
    def title(self):
        """Возвращает название задачи на основе этапа"""
        if self.stage:
            return f"{self.stage.operation} - {self.stage.order.name if self.stage.order else 'Заказ'}"
        return f"Задача #{self.id}"
    
    @property
    def plan_quantity(self):
        """Возвращает план задачи (для совместимости с фронтендом)"""
        return self.quantity
    
    @property
    def started_at(self):
        """Возвращает дату начала задачи"""
        return self.created_at

    def consume_materials(self, delta_completed_quantity: int):
        """Учитывает расход сырья при выполнении работы для приращения delta_completed_quantity"""
        if not self.service or not delta_completed_quantity:
            return
        
        from apps.services.models import ServiceMaterial
        
        # Получаем все материалы для данной услуги
        service_materials = ServiceMaterial.objects.filter(service=self.service)
        
        for service_material in service_materials:
            material = service_material.material
            # Рассчитываем количество израсходованного сырья ТОЛЬКО для дельты
            consumed_amount = service_material.amount * Decimal(str(delta_completed_quantity))
            
            # Обновляем количество на складе
            if material.quantity >= consumed_amount:
                material.quantity -= consumed_amount
                material.save()
                
                # Логируем расход
                try:
                    from apps.inventory.models import MaterialConsumption
                    MaterialConsumption.objects.create(
                        material=material,
                        quantity=consumed_amount,
                        employee_task=self,
                        workshop=self.stage.workshop,
                        order=self.stage.order
                    )
                except Exception as e:
                    # Логируем ошибку, но не прерываем выполнение
                    print(f"Ошибка создания записи расхода: {e}")
            else:
                # Если недостаточно сырья, создаем предупреждение
                try:
                    from apps.notifications.models import Notification
                    Notification.objects.create(
                        user=self.employee,
                        title="Недостаточно сырья",
                        message=f"Недостаточно материала {material.name} для выполнения задачи",
                        notification_type="warning"
                    )
                except Exception as e:
                    # Логируем ошибку, но не прерываем выполнение
                    print(f"Ошибка создания уведомления: {e}")

@receiver(pre_save, sender=EmployeeTask)
def create_defect_on_defective_change(sender, instance, **kwargs):
    """Создает записи браков в новой системе при изменении defective_quantity"""
    if instance.pk:
        try:
            old_instance = EmployeeTask.objects.get(pk=instance.pk)
            # Дельта выполненного для последующего списания материалов
            delta_completed = int(instance.completed_quantity) - int(old_instance.completed_quantity)
            instance._delta_completed_quantity = max(delta_completed, 0)

            # Создание браков в новой системе
            if instance.defective_quantity > old_instance.defective_quantity:
                from apps.defects.models import Defect
                defect_quantity = instance.defective_quantity - old_instance.defective_quantity
                
                # Создаем записи браков для каждого единицы брака
                for _ in range(defect_quantity):
                    Defect.objects.create(
                        employee_task=instance,
                        product=instance.stage.order_item.product if instance.stage.order_item else None,
                        user=instance.employee,
                        status='pending'  # Ожидает подтверждения мастера
                    )
        except EmployeeTask.DoesNotExist:
            instance._delta_completed_quantity = 0
    else:
        instance._delta_completed_quantity = 0

@receiver(post_save, sender=EmployeeTask)
def update_earnings_and_materials(sender, instance, created, **kwargs):
    """Обновляет заработок и учитывает расход сырья при изменении задачи"""
    try:
        with transaction.atomic():
            # Рассчитываем заработок по текущим значениям
            instance.calculate_earnings()
            # Списываем материалы по дельте; если запись только что создана и есть выполненное количество, спишем сразу
            delta = getattr(instance, '_delta_completed_quantity', None)
            if delta is None:
                delta = instance.completed_quantity if created else 0
            if int(delta) > 0:
                instance.consume_materials(int(delta))
            # Обновляем агрегаты в базе без рекурсии
            EmployeeTask.objects.filter(pk=instance.pk).update(
                earnings=instance.earnings,
                penalties=instance.penalties,
                net_earnings=instance.net_earnings
            )
    except Exception as e:
        # Логируем ошибку, но не прерываем выполнение
        print(f"Ошибка в update_earnings_and_materials: {e}")
