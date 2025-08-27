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
    
    # Пользовательская цена за единицу для данного назначения (перекрывает цену услуги)
    custom_unit_price = models.DecimalField('Индивидуальная цена за единицу', max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Связь с услугой через цех
    @property
    def service(self):
        """Получаем услугу через цех этапа и название операции"""
        if self.stage and self.stage.workshop and self.stage.operation:
            from apps.services.models import Service
            try:
                # Сначала ищем услугу по цеху и названию операции
                service = Service.objects.filter(
                    workshop=self.stage.workshop, 
                    name=self.stage.operation,
                    is_active=True
                ).first()
                
                # Если не найдена, ищем первую активную услугу для цеха
                if not service:
                    service = Service.objects.filter(
                        workshop=self.stage.workshop, 
                        is_active=True
                    ).first()
                
                return service
            except Exception:
                return None
        return None

    class Meta:
        verbose_name = 'Задача сотрудника'
        verbose_name_plural = 'Задачи сотрудников'

    def __str__(self):
        return f"Задача {self.employee} - {self.stage}"

    def calculate_earnings(self):
        """Рассчитывает заработок, штрафы и чистый заработок"""
        # Базовая ставка за единицу работы (если услуга не найдена)
        BASE_RATE = Decimal('100.00')  # 100 рублей за единицу
        BASE_PENALTY_RATE = Decimal('50.00')  # 50 рублей за единицу брака
        
        # Если установлена индивидуальная цена от мастера — используем её
        if self.custom_unit_price is not None:
            service_price = Decimal(str(self.custom_unit_price))
            # Штраф берём из услуги, если доступен, иначе базовый
            if self.service:
                penalty_rate = self.service.defect_penalty
            else:
                penalty_rate = BASE_PENALTY_RATE
        else:
            if self.service:
                # Используем цены из услуги
                service_price = self.service.service_price
                penalty_rate = self.service.defect_penalty
            else:
                # Используем базовые ставки
                service_price = BASE_RATE
                penalty_rate = BASE_PENALTY_RATE
        
        # Заработок за выполненную работу
        self.earnings = Decimal(str(self.completed_quantity)) * service_price
        
        # Штрафы за брак
        self.penalties = Decimal(str(self.defective_quantity)) * penalty_rate
        
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
    """Создает записи браков в новой системе при изменении defective_quantity и сохраняет предыдущее значение net_earnings"""
    if instance.pk:
        try:
            old_instance = EmployeeTask.objects.get(pk=instance.pk)
            # Дельта выполненного для последующего списания материалов
            delta_completed = int(instance.completed_quantity) - int(old_instance.completed_quantity)
            instance._delta_completed_quantity = max(delta_completed, 0)
            # Сохраняем старое значение чистого заработка для корректного обновления баланса
            instance._old_net_earnings = Decimal(str(old_instance.net_earnings or 0))

            # Создание браков в новой системе
            if instance.defective_quantity > old_instance.defective_quantity:
                from apps.defects.models import Defect
                defect_quantity = instance.defective_quantity - old_instance.defective_quantity
                
                # Создаем записи браков для каждого единицы брака
                for _ in range(defect_quantity):
                    Defect.objects.create(
                        employee_task=instance,
                        product=(
                            instance.stage.order_item.product
                            if instance.stage.order_item
                            else (instance.stage.order.product if getattr(instance.stage, 'order', None) and getattr(instance.stage.order, 'product', None) else None)
                        ),
                        user=instance.employee,
                        status='pending'  # Ожидает подтверждения мастера
                    )
        except EmployeeTask.DoesNotExist:
            instance._delta_completed_quantity = 0
            instance._old_net_earnings = Decimal('0')
    else:
        instance._delta_completed_quantity = 0
        instance._old_net_earnings = Decimal('0')

@receiver(post_save, sender=EmployeeTask)
def update_earnings_and_materials(sender, instance, created, **kwargs):
    """Обновляет заработок, учитывает расход сырья и пополняет баланс пользователя"""
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
            # Пополняем баланс сотрудника разницей чистого заработка
            old_net = getattr(instance, '_old_net_earnings', Decimal('0'))
            new_net = Decimal(str(instance.net_earnings or 0))
            delta_net = new_net - old_net
            if delta_net != 0:
                from django.db.models import F
                User.objects.filter(pk=instance.employee_id).update(balance=F('balance') + delta_net)
    except Exception as e:
        # Логируем ошибку, но не прерываем выполнение
        print(f"Ошибка в update_earnings_and_materials: {e}")
