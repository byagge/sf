from django.core.management.base import BaseCommand
from django.db import transaction
from apps.orders.models import OrderStage, Order, OrderItem
from apps.products.models import Product
from django.db.models import Q

class Command(BaseCommand):
    help = 'Полностью удаляет стеклянные товары из заказов в цехах после ID5'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Показать что будет удалено без фактического удаления',
        )
        parser.add_argument(
            '--workshop-id',
            type=int,
            help='Обработать только конкретный цех (ID >= 6)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        workshop_id = options.get('workshop_id')
        
        self.stdout.write('Начинаем удаление стеклянных товаров из заказов после пресса...')
        
        # Определяем цеха для обработки
        if workshop_id:
            if workshop_id < 6:
                self.stdout.write(
                    self.style.ERROR(f'Цех ID {workshop_id} не требует обработки (только ID >= 6)')
                )
                return
            workshop_ids = [workshop_id]
        else:
            # Все цеха с ID >= 6
            workshop_ids = list(range(6, 20))  # Предполагаем максимум ID 19
        
        total_removed_items = 0
        total_updated_orders = 0
        
        for workshop_id in workshop_ids:
            self.stdout.write(f'\nОбрабатываем цех ID {workshop_id}...')
            
            # Находим все этапы в этом цехе
            stages = OrderStage.objects.filter(
                workshop_id=workshop_id,
                status__in=['in_progress', 'waiting', 'partial']
            ).select_related('order', 'workshop')
            
            workshop_removed_items = 0
            workshop_updated_orders = 0
            processed_orders = set()
            
            for stage in stages:
                if not stage.order or stage.order.id in processed_orders:
                    continue
                    
                order = stage.order
                processed_orders.add(order.id)
                
                # Находим все стеклянные товары в заказе
                glass_items = order.items.filter(
                    product__is_glass=True
                )
                
                if glass_items.exists():
                    self.stdout.write(f'  Заказ {order.id}: найдено {glass_items.count()} стеклянных товаров')
                    
                    if dry_run:
                        for item in glass_items:
                            self.stdout.write(
                                f'    [DRY RUN] Будет удален товар {item.id}: {item.product.name if item.product else "Без названия"}'
                            )
                    else:
                        # Удаляем стеклянные товары
                        with transaction.atomic():
                            for item in glass_items:
                                self.stdout.write(
                                    f'    Удаляем товар {item.id}: {item.product.name if item.product else "Без названия"}'
                                )
                                item.delete()
                                workshop_removed_items += 1
                    
                    workshop_updated_orders += 1
            
            self.stdout.write(f'Цех ID {workshop_id}: удалено {workshop_removed_items} товаров из {workshop_updated_orders} заказов')
            total_removed_items += workshop_removed_items
            total_updated_orders += workshop_updated_orders
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'\n[DRY RUN] Всего будет удалено: {total_removed_items} товаров из {total_updated_orders} заказов')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'\nУдаление завершено! Всего удалено: {total_removed_items} товаров из {total_updated_orders} заказов')
            )