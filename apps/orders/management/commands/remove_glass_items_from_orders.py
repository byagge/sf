from django.core.management.base import BaseCommand
from django.db import transaction
from apps.orders.models import OrderStage, Order, OrderItem
from apps.products.models import Product
from django.db.models import Q

class Command(BaseCommand):
    help = 'Диагностика стеклянных товаров в цехах'

    def handle(self, *args, **options):
        self.stdout.write('=== ДИАГНОСТИКА СТЕКЛЯННЫХ ТОВАРОВ ===\n')
        
        # Проверяем все цеха с ID >= 6
        for workshop_id in range(6, 20):
            self.stdout.write(f'--- Цех ID {workshop_id} ---')
            
            # Находим все этапы в этом цехе
            stages = OrderStage.objects.filter(
                workshop_id=workshop_id,
                status__in=['in_progress', 'waiting', 'partial', 'done']
            ).select_related('order', 'workshop')
            
            self.stdout.write(f'  Всего этапов: {stages.count()}')
            
            if stages.exists():
                # Проверяем заказы на стеклянные товары
                orders_with_glass = 0
                total_glass_items = 0
                
                for stage in stages:
                    if stage.order:
                        glass_items = stage.order.items.filter(product__is_glass=True)
                        if glass_items.exists():
                            orders_with_glass += 1
                            total_glass_items += glass_items.count()
                            self.stdout.write(f'    Заказ {stage.order.id}: {glass_items.count()} стеклянных товаров')
                            for item in glass_items:
                                self.stdout.write(f'      - {item.id}: {item.product.name if item.product else "Без названия"}')
                
                self.stdout.write(f'  Заказов со стеклянными товарами: {orders_with_glass}')
                self.stdout.write(f'  Всего стеклянных товаров: {total_glass_items}')
            else:
                self.stdout.write('  Нет этапов в этом цехе')
            
            self.stdout.write('')
        
        # Общая статистика по стеклянным товарам
        self.stdout.write('=== ОБЩАЯ СТАТИСТИКА ===')
        all_glass_items = OrderItem.objects.filter(product__is_glass=True)
        self.stdout.write(f'Всего стеклянных товаров в системе: {all_glass_items.count()}')
        
        # Проверяем, в каких цехах есть этапы
        workshops_with_stages = OrderStage.objects.values_list('workshop_id', flat=True).distinct()
        self.stdout.write(f'Цеха с этапами: {sorted(workshops_with_stages)}')
        
        # Проверяем заказы со стеклянными товарами
        orders_with_glass = Order.objects.filter(items__product__is_glass=True).distinct()
        self.stdout.write(f'Заказов со стеклянными товарами: {orders_with_glass.count()}')
        
        for order in orders_with_glass[:5]:  # Показываем первые 5
            glass_count = order.items.filter(product__is_glass=True).count()
            self.stdout.write(f'  Заказ {order.id}: {glass_count} стеклянных товаров')