from django.core.management.base import BaseCommand
from django.db import transaction
from apps.orders.models import OrderStage
from apps.products.models import Product
from django.db.models import Q

class Command(BaseCommand):
    help = 'Исправляет стеклянные товары в цехах после ID5 (после пресса)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Показать что будет изменено без фактического изменения',
        )
        parser.add_argument(
            '--workshop-id',
            type=int,
            help='Исправить только конкретный цех (ID >= 6)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        workshop_id = options.get('workshop_id')
        
        self.stdout.write('Начинаем исправление стеклянных товаров после пресса...')
        
        # Определяем цеха для обработки
        if workshop_id:
            if workshop_id < 6:
                self.stdout.write(
                    self.style.ERROR(f'Цех ID {workshop_id} не требует исправления (только ID >= 6)')
                )
                return
            workshop_ids = [workshop_id]
        else:
            # Все цеха с ID >= 6
            workshop_ids = list(range(6, 20))  # Предполагаем максимум ID 19
        
        total_fixed = 0
        
        for workshop_id in workshop_ids:
            self.stdout.write(f'\nОбрабатываем цех ID {workshop_id}...')
            
            # Находим все этапы в этом цехе
            stages = OrderStage.objects.filter(
                workshop_id=workshop_id,
                status__in=['in_progress', 'waiting', 'partial']
            ).select_related('order', 'order_item__product', 'workshop')
            
            workshop_fixed = 0
            
            for stage in stages:
                has_glass_items = False
                
                # Проверяем, есть ли стеклянные товары в заказе
                if stage.order:
                    # Проверяем все товары заказа
                    glass_items = stage.order.items.filter(
                        product__is_glass=True
                    ).exists()
                    
                    if glass_items:
                        has_glass_items = True
                        self.stdout.write(
                            f'  Найден этап {stage.id} с стеклянными товарами в заказе {stage.order.id}'
                        )
                
                # Проверяем, есть ли стеклянный товар в order_item
                if stage.order_item and stage.order_item.product and stage.order_item.product.is_glass:
                    has_glass_items = True
                    self.stdout.write(
                        f'  Найден этап {stage.id} с стеклянным товаром в order_item'
                    )
                
                if has_glass_items:
                    if dry_run:
                        self.stdout.write(
                            self.style.WARNING(f'  [DRY RUN] Будет удален этап {stage.id}')
                        )
                    else:
                        # Удаляем этап со стеклянными товарами
                        stage.delete()
                        self.stdout.write(
                            self.style.SUCCESS(f'  Удален этап {stage.id}')
                        )
                    workshop_fixed += 1
            
            self.stdout.write(f'Цех ID {workshop_id}: исправлено {workshop_fixed} этапов')
            total_fixed += workshop_fixed
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'\n[DRY RUN] Всего будет исправлено: {total_fixed} этапов')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'\nИсправление завершено! Всего исправлено: {total_fixed} этапов')
            )