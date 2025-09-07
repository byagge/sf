from django.db import models
from apps.inventory.models import RawMaterial
from apps.operations.workshops.models import Workshop
from apps.services.models import Service

# Create your models here.

class Product(models.Model):
    PRODUCT_TYPES = [
        ("door", "Дверь"),
        # Можно добавить другие типы позже
    ]
    
    GLASS_TYPES = [
        ("sandblasted", "Пескоструйный"),
        ("uv", "УФ"),
    ]
    
    name = models.CharField('Наименование', max_length=255)
    type = models.CharField('Тип', max_length=50, choices=PRODUCT_TYPES, default="door")
    description = models.TextField('Описание', blank=True)
    is_glass = models.BooleanField('Стеклянный', default=False)
    glass_type = models.CharField(
        'Тип стекла', 
        max_length=20, 
        choices=GLASS_TYPES, 
        null=True, 
        blank=True,
        help_text='Указывается только для стеклянных изделий'
    )
    img = models.ImageField('Изображение', upload_to='products/', blank=True, null=True)
    services = models.ManyToManyField(Service, related_name="products", verbose_name="Услуги для продукта")
    price = models.DecimalField('Цена за продукт', max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)

    class Meta:
        verbose_name = 'Продукт'
        verbose_name_plural = 'Продукты'

    def __str__(self):
        return self.name

    def get_materials_with_amounts(self):
        """
        Возвращает словарь {материал: общее_количество} по всем выбранным услугам.
        """
        from collections import defaultdict
        materials = defaultdict(float)
        for service in self.services.all():
            for sm in service.service_materials.all():
                materials[sm.material] += float(sm.amount)
        return dict(materials)

    def get_cost_price(self):
        """
        Себестоимость: сумма цен услуг + сумма (расход сырья * цена сырья) по всем услугам.
        """
        total_service_price = sum(float(service.service_price) for service in self.services.all())
        materials = self.get_materials_with_amounts()
        total_material_cost = sum(float(material.price) * amount for material, amount in materials.items())
        return total_service_price + total_material_cost

class MaterialConsumption(models.Model):
    product = models.ForeignKey('Product', on_delete=models.CASCADE, verbose_name='Продукт')
    workshop = models.ForeignKey(Workshop, on_delete=models.CASCADE, verbose_name='Цех')
    material = models.ForeignKey(RawMaterial, on_delete=models.CASCADE, verbose_name='Сырьё')
    amount = models.FloatField('Расход на единицу продукции')

    class Meta:
        verbose_name = 'Норма расхода сырья'
        verbose_name_plural = 'Нормы расхода сырья'
        unique_together = ('product', 'workshop', 'material')

    def __str__(self):
        return f'{self.product} - {self.workshop}: {self.material} ({self.amount})'
