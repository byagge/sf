from django.db import models

# Create your models here.

class FinishedGood(models.Model):
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='finished_goods', verbose_name='Продукт')
    quantity = models.PositiveIntegerField('Количество', default=1)
    order = models.ForeignKey('orders.Order', on_delete=models.SET_NULL, null=True, blank=True, related_name='finished_goods', verbose_name='Заказ')
    received_at = models.DateTimeField('Дата поступления', auto_now_add=True)
    status = models.CharField('Статус', max_length=20, choices=[('stock', 'На складе'), ('issued', 'Выдано')], default='stock')
    issued_at = models.DateTimeField('Дата выдачи', null=True, blank=True)
    recipient = models.CharField('Получатель', max_length=255, blank=True)
    comment = models.CharField('Комментарий', max_length=255, blank=True)

    class Meta:
        verbose_name = 'Готовая продукция'
        verbose_name_plural = 'Готовая продукция (склад)'
        ordering = ['-received_at']

    def __str__(self):
        return f"{self.product} x{self.quantity} ({self.get_status_display()})"

def create_example_finished_good():
    from apps.products.models import Product
    from apps.orders.models import Order
    product = Product.objects.first()
    order = Order.objects.first()
    if not product:
        print('Нет продуктов для примера!')
        return
    fg = FinishedGood.objects.create(
        product=product,
        quantity=10,
        order=order,
        status='stock',
        recipient='Иванов Иван',
        comment='Тестовая партия готовой продукции'
    )
    print('Пример готовой продукции создан:', fg)
