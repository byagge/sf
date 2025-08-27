from django.core.management.base import BaseCommand
from apps.orders.models import Order, OrderStage
from apps.operations.workshops.models import Workshop


class Command(BaseCommand):
    help = 'Исправляет существующие заказы с стеклянными товарами для разделения по цехам'

    def handle(self, *args, **options):
        self.stdout.write('Начинаем исправление заказов с стеклянными товарами...')
        
        # Получаем все заказы с позициями
        orders_with_items = Order.objects.filter(items__isnull=False).distinct()
        
        fixed_count = 0
        skipped_count = 0
        
        for order in orders_with_items:
            try:
                # Проверяем, есть ли в заказе стеклянные товары
                has_glass = any(item.product and item.product.is_glass for item in order.items.all())
                
                if not has_glass:
                    skipped_count += 1
                    continue
                
                self.stdout.write(f'Обрабатываем заказ {order.id}: {order.name}')
                
                # Удаляем существующие этапы для этого заказа
                OrderStage.objects.filter(order=order).delete()
                
                # Создаем новые этапы с разделением
                from apps.orders.models import create_order_stages
                create_order_stages(order)
                
                fixed_count += 1
                self.stdout.write(f'  ✓ Заказ {order.id} исправлен')
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'  ✗ Ошибка при обработке заказа {order.id}: {e}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Исправление завершено. Исправлено: {fixed_count}, Пропущено: {skipped_count}'
            )
        ) 