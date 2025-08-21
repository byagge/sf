"""
Optimized Order models with caching and performance improvements
"""

from django.db import models
from django.core.cache import cache
from django.db.models import Prefetch, Q, Sum, Count
from django.utils import timezone
from datetime import datetime, time, timedelta
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

class Order(models.Model):
    STATUS_CHOICES = [
        ('production', 'В производстве'),
        ('stock', 'На складе'),
        ('shipped', 'Отправлен клиенту'),
        ('new', 'Новая'),
    ]
    
    name = models.CharField('Название заявки', max_length=200, db_index=True)
    client = models.ForeignKey('clients.Client', on_delete=models.CASCADE, related_name='orders', verbose_name='Клиент', db_index=True)
    workshop = models.ForeignKey('operations_workshops.Workshop', on_delete=models.SET_NULL, null=True, blank=True, related_name='orders', verbose_name='Этап (цех)', db_index=True)
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='orders', verbose_name='Продукт', null=True, blank=True, db_index=True)
    quantity = models.PositiveIntegerField('Количество', default=1, db_index=True)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True, db_index=True)
    status = models.CharField('Статус', max_length=30, choices=STATUS_CHOICES, default='production', db_index=True)
    comment = models.CharField('Комментарий', max_length=255, blank=True)
    expenses = models.FloatField('Расходы', default=0, editable=False, db_index=True)
    
    # Добавляем поля для оптимизации
    updated_at = models.DateTimeField('Дата обновления', auto_now=True, db_index=True)
    priority = models.PositiveSmallIntegerField('Приоритет', default=5, db_index=True)
    estimated_completion = models.DateTimeField('Ожидаемое завершение', null=True, blank=True, db_index=True)

    class Meta:
        verbose_name = 'Заявка'
        verbose_name_plural = 'Заявки'
        ordering = ['-priority', '-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['client', 'status']),
            models.Index(fields=['workshop', 'status']),
            models.Index(fields=['priority', 'estimated_completion']),
        ]

    def __str__(self):
        product_part = f" — {self.product} x{self.quantity}" if self.product else ""
        return f"{self.name} ({self.client}){product_part} [{self.status_display}]"

    @property
    def status_display(self):
        return dict(self.STATUS_CHOICES).get(self.status, self.status)

    @property
    def total_done_count(self):
        """Кэшированное количество выполненных задач"""
        cache_key = f'order_{self.id}_total_done'
        result = cache.get(cache_key)
        if result is None:
            result = sum(stage.done_count for stage in self.stages.all())
            cache.set(cache_key, result, 300)  # 5 минут
        return result

    @property
    def total_defective_count(self):
        """Кэшированное количество брака"""
        cache_key = f'order_{self.id}_total_defective'
        result = cache.get(cache_key)
        if result is None:
            result = sum(stage.defective_count for stage in self.stages.all())
            cache.set(cache_key, result, 300)  # 5 минут
        return result

    @property
    def total_quantity(self):
        """Общее количество товаров в заказе"""
        cache_key = f'order_{self.id}_total_quantity'
        result = cache.get(cache_key)
        if result is None:
            items_sum = sum(item.quantity for item in self.items.all())
            result = items_sum if items_sum > 0 else (self.quantity or 0)
            cache.set(cache_key, result, 300)  # 5 минут
        return result

    @property
    def has_glass_items(self):
        """Проверяет, есть ли в заказе стеклянные изделия"""
        cache_key = f'order_{self.id}_has_glass'
        result = cache.get(cache_key)
        if result is None:
            result = any(item.product.is_glass for item in self.items.all() if item.product)
            cache.set(cache_key, result, 300)  # 5 минут
        return result

    @property
    def glass_items(self):
        """Возвращает все стеклянные позиции заказа"""
        cache_key = f'order_{self.id}_glass_items'
        result = cache.get(cache_key)
        if result is None:
            result = [item for item in self.items.all() if item.product and item.product.is_glass]
            cache.set(cache_key, result, 300)  # 5 минут
        return result

    @property
    def regular_items(self):
        """Возвращает все обычные (не стеклянные) позиции заказа"""
        cache_key = f'order_{self.id}_regular_items'
        result = cache.get(cache_key)
        if result is None:
            result = [item for item in self.items.all() if item.product and not item.product.is_glass]
            cache.set(cache_key, result, 300)  # 5 минут
        return result

    def get_order_summary(self):
        """Возвращает сводку по всему заказу с кэшированием"""
        cache_key = f'order_{self.id}_summary'
        summary = cache.get(cache_key)
        
        if summary is None:
            summary = {
                'order_id': self.id,
                'order_name': self.name,
                'client': self.client.name if self.client else '',
                'status': self.status,
                'total_quantity': self.total_quantity,
                'has_glass_items': self.has_glass_items,
                'items': [],
                'glass_items': [],
                'regular_items': [],
            }
            
            for item in self.items.all():
                item_summary = {
                    'id': item.id,
                    'product': item.product.name if item.product else '',
                    'quantity': item.quantity,
                    'size': item.size,
                    'color': item.color,
                    'is_glass': item.product.is_glass if item.product else False,
                    'glass_type': item.get_glass_type_display(),
                    'paint_type': item.paint_type,
                    'paint_color': item.paint_color,
                }
                
                summary['items'].append(item_summary)
                
                if item.product and item.product.is_glass:
                    summary['glass_items'].append(item_summary)
                else:
                    summary['regular_items'].append(item_summary)
            
            # Кэшируем на 10 минут
            cache.set(cache_key, summary, 600)
        
        return summary

    def clear_cache(self):
        """Очищает все кэши для этого заказа"""
        cache_keys = [
            f'order_{self.id}_total_done',
            f'order_{self.id}_total_defective',
            f'order_{self.id}_total_quantity',
            f'order_{self.id}_has_glass',
            f'order_{self.id}_glass_items',
            f'order_{self.id}_regular_items',
            f'order_{self.id}_summary',
        ]
        cache.delete_many(cache_keys)

    @classmethod
    def get_active_orders(cls):
        """Получает активные заказы с оптимизацией"""
        return cls.objects.filter(
            status__in=['production', 'new']
        ).select_related(
            'client', 'workshop', 'product'
        ).prefetch_related(
            'items__product',
            'stages'
        ).order_by('-priority', '-created_at')

    @classmethod
    def get_orders_by_status(cls, status):
        """Получает заказы по статусу с оптимизацией"""
        cache_key = f'orders_status_{status}'
        orders = cache.get(cache_key)
        
        if orders is None:
            orders = list(cls.objects.filter(status=status).select_related(
                'client', 'workshop', 'product'
            ).prefetch_related(
                'items__product'
            ).order_by('-created_at')[:100])  # Ограничиваем для кэша
            
            cache.set(cache_key, orders, 300)  # 5 минут
        
        return orders

    @classmethod
    def get_orders_by_client(cls, client_id):
        """Получает заказы клиента с оптимизацией"""
        cache_key = f'orders_client_{client_id}'
        orders = cache.get(cache_key)
        
        if orders is None:
            orders = list(cls.objects.filter(client_id=client_id).select_related(
                'workshop', 'product'
            ).prefetch_related(
                'items__product'
            ).order_by('-created_at'))
            
            cache.set(cache_key, orders, 600)  # 10 минут
        
        return orders

    def save(self, *args, **kwargs):
        """Переопределяем save для очистки кэша"""
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if not is_new:
            self.clear_cache()
        
        # Очищаем связанные кэши
        cache.delete(f'orders_status_{self.status}')
        if self.client_id:
            cache.delete(f'orders_client_{self.client_id}')

# Сигналы для автоматической очистки кэша
@receiver(post_save, sender=Order)
def clear_order_cache(sender, instance, **kwargs):
    """Очищает кэш при сохранении заказа"""
    instance.clear_cache()

@receiver(post_delete, sender=Order)
def clear_order_cache_on_delete(sender, instance, **kwargs):
    """Очищает кэш при удалении заказа"""
    instance.clear_cache()

# Оптимизированные менеджеры для моделей
class OrderManager(models.Manager):
    def get_queryset(self):
        """Оптимизированный QuerySet по умолчанию"""
        return super().get_queryset().select_related(
            'client', 'workshop', 'product'
        ).prefetch_related(
            'items__product'
        )

    def with_statistics(self):
        """QuerySet с предварительно загруженной статистикой"""
        return self.get_queryset().annotate(
            total_items=Count('items'),
            total_stages=Count('stages'),
            total_defects=Sum('stages__defective_count'),
            total_completed=Sum('stages__done_count'),
        )

    def by_priority(self, priority):
        """Заказы по приоритету"""
        return self.filter(priority=priority).order_by('-created_at')

    def urgent_orders(self):
        """Срочные заказы (высокий приоритет)"""
        return self.filter(priority__gte=8).order_by('-created_at')

    def overdue_orders(self):
        """Просроченные заказы"""
        now = timezone.now()
        return self.filter(
            estimated_completion__lt=now,
            status__in=['production', 'new']
        ).order_by('estimated_completion')

# Применяем менеджер к модели
Order.objects = OrderManager() 