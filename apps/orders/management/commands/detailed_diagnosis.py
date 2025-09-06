from django.core.management.base import BaseCommand
from apps.orders.models import OrderStage, Order, OrderItem
from apps.products.models import Product

class Command(BaseCommand):
    help = 'Детальная диагностика этапов в цехах 6-7'

    def handle(self, *args, **options):
        self.stdout.write('=== ДЕТАЛЬНАЯ ДИАГНОСТИКА ЦЕХОВ 6-7 ===\n')
        
        for workshop_id in [6, 7]:
            self.stdout.write(f'--- Цех ID {workshop_id} ---')
            
            # ВСЕ этапы в этом цехе (без фильтра по статусу)
            all_stages = OrderStage.objects.filter(workshop_id=workshop_id)
            self.stdout.write(f'  Всего этапов (все статусы): {all_stages.count()}')
            
            if all_stages.exists():
                # Показываем все статусы
                statuses = all_stages.values_list('status', flat=True).distinct()
                self.stdout.write(f'  Статусы этапов: {list(statuses)}')
                
                # Показываем первые 5 этапов
                for stage in all_stages[:5]:
                    self.stdout.write(f'    Этап {stage.id}: статус {stage.status}, заказ {stage.order_id if stage.order else "N/A"}')
                
                # Проверяем заказы на стеклянные товары
                orders_with_glass = 0
                total_glass_items = 0
                
                for stage in all_stages:
                    if stage.order:
                        glass_items = stage.order.items.filter(product__is_glass=True)
                        if glass_items.exists():
                            orders_with_glass += 1
                            total_glass_items += glass_items.count()
                            self.stdout.write(f'    Заказ {stage.order.id}: {glass_items.count()} стеклянных товаров')
                            for item in glass_items:
                                self.stdout.write(f'      - {item.id}: {item.product.name if item.product else "Без названия"} (is_glass: {item.product.is_glass if item.product else "N/A"})')
                
                self.stdout.write(f'  Заказов со стеклянными товарами: {orders_with_glass}')
                self.stdout.write(f'  Всего стеклянных товаров: {total_glass_items}')
            else:
                self.stdout.write('  Нет этапов в этом цехе')
            
            self.stdout.write('')
        
        # Проверяем все цеха с этапами
        self.stdout.write('=== ВСЕ ЦЕХА С ЭТАПАМИ ===')
        workshops_with_stages = OrderStage.objects.values_list('workshop_id', flat=True).distinct()
        self.stdout.write(f'Цеха с этапами: {sorted(workshops_with_stages)}')
        
        # Показываем статистику по каждому цеху
        for workshop_id in sorted(workshops_with_stages):
            stages_count = OrderStage.objects.filter(workshop_id=workshop_id).count()
            self.stdout.write(f'  Цех {workshop_id}: {stages_count} этапов')