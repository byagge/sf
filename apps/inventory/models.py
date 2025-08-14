from django.db import models
import uuid

class RawMaterial(models.Model):
    name = models.CharField('Название', max_length=100)
    code = models.CharField('Артикул/Код', max_length=50, unique=True, blank=True)
    size = models.CharField('Размер', max_length=50, blank=True)
    unit = models.CharField('Ед. измерения', max_length=20)
    quantity = models.DecimalField('Количество', max_digits=12, decimal_places=3, default=0)
    min_quantity = models.DecimalField('Мин. остаток', max_digits=12, decimal_places=3, default=0)
    price = models.DecimalField('Цена за единицу', max_digits=10, decimal_places=2, default=0)
    description = models.TextField('Описание', blank=True)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)

    class Meta:
        verbose_name = 'Сырье/материал'
        verbose_name_plural = 'Сырье и материалы'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.code})"

    def save(self, *args, **kwargs):
        # Генерируем код автоматически, если он не указан или пустой
        if not self.code or self.code.strip() == '':
            # Генерируем уникальный код на основе названия и случайного числа
            base_code = ''.join(c.upper() for c in self.name if c.isalpha())[:3]
            if not base_code:
                base_code = 'MAT'
            
            # Добавляем случайное число для уникальности
            unique_id = str(uuid.uuid4())[:8].upper()
            self.code = f"{base_code}-{unique_id}"
            
            # Проверяем уникальность и генерируем новый код, если нужно
            # Используем exclude для исключения текущего объекта при обновлении
            while RawMaterial.objects.filter(code=self.code).exclude(id=self.id).exists():
                unique_id = str(uuid.uuid4())[:8].upper()
                self.code = f"{base_code}-{unique_id}"
        
        super().save(*args, **kwargs)

    @property
    def total_value(self):
        """Общая стоимость материала на складе"""
        return self.quantity * self.price

class MaterialIncoming(models.Model):
    """Модель для истории приходов материалов"""
    material = models.ForeignKey(RawMaterial, on_delete=models.CASCADE, related_name='incomings', verbose_name='Материал')
    quantity = models.DecimalField('Количество прихода', max_digits=12, decimal_places=3)
    price_per_unit = models.DecimalField('Цена за единицу', max_digits=10, decimal_places=2, null=True, blank=True)
    total_value = models.DecimalField('Общая стоимость', max_digits=12, decimal_places=2, null=True, blank=True)
    notes = models.TextField('Примечания', blank=True, null=True)
    created_at = models.DateTimeField('Дата прихода', auto_now_add=True)
    
    class Meta:
        verbose_name = 'Приход материала'
        verbose_name_plural = 'Приходы материалов'
        ordering = ['-created_at']

    def __str__(self):
        return f"Приход {self.material.name} - {self.quantity} {self.material.unit}"

    def save(self, *args, **kwargs):
        # Автоматически рассчитываем общую стоимость
        if self.price_per_unit is not None and not self.total_value:
            self.total_value = self.quantity * self.price_per_unit
        super().save(*args, **kwargs) 

class MaterialConsumption(models.Model):
    """Учет расхода сырья при выполнении задач"""
    material = models.ForeignKey(RawMaterial, on_delete=models.CASCADE, related_name='consumptions')
    quantity = models.DecimalField('Количество израсходовано', max_digits=12, decimal_places=3)
    employee_task = models.ForeignKey('employee_tasks.EmployeeTask', on_delete=models.CASCADE, related_name='material_consumptions')
    workshop = models.ForeignKey('operations_workshops.Workshop', on_delete=models.CASCADE, related_name='inventory_consumptions')
    order = models.ForeignKey('orders.Order', on_delete=models.CASCADE)
    consumed_at = models.DateTimeField('Дата расхода', auto_now_add=True)
    
    class Meta:
        verbose_name = 'Расход сырья'
        verbose_name_plural = 'Расходы сырья'
        ordering = ['-consumed_at']
    
    def __str__(self):
        return f"{self.material.name} - {self.quantity} ({self.workshop.name})" 