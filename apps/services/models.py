from django.db import models
from apps.operations.workshops.models import Workshop
from apps.inventory.models import RawMaterial

# Create your models here.

class Service(models.Model):
    name = models.CharField("Название услуги", max_length=255)
    description = models.TextField("Описание", blank=True)
    unit = models.CharField("Единица измерения", max_length=50, default="услуга")
    workshop = models.ForeignKey(Workshop, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Цех")
    service_price = models.DecimalField("Оплата за услугу", max_digits=12, decimal_places=5, default=0)
    defect_penalty = models.DecimalField("Штраф за брак", max_digits=12, decimal_places=5, default=0)
    materials = models.ManyToManyField(
        RawMaterial,
        through='ServiceMaterial',
        related_name='services',
        verbose_name="Список сырья"
    )
    is_active = models.BooleanField("Активна", default=True)
    created_at = models.DateTimeField("Создана", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлена", auto_now=True)

    class Meta:
        verbose_name = "Услуга"
        verbose_name_plural = "Услуги"
        ordering = ["name"]

    def __str__(self):
        return self.name

class ServiceMaterial(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='service_materials')
    material = models.ForeignKey(RawMaterial, on_delete=models.CASCADE, related_name='service_materials')
    amount = models.DecimalField("Расход сырья на услугу", max_digits=12, decimal_places=3)

    class Meta:
        unique_together = ('service', 'material')
        verbose_name = "Сырьё для услуги"
        verbose_name_plural = "Сырьё для услуги"

    def __str__(self):
        return f"{self.service} — {self.material} ({self.amount})"
