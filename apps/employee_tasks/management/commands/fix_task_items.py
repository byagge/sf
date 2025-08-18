from django.core.management.base import BaseCommand
from apps.orders.models import OrderStage, OrderItem
from apps.employee_tasks.models import EmployeeTask

class Command(BaseCommand):
    help = 'Исправляет связь этапов с позициями заказа'

    def handle(self, *args, **options):
        self.stdout.write("=== Исправление связи этапов с позициями заказа ===")
        
        # Находим этапы без позиций заказа
        stages_without_items = OrderStage.objects.filter(order_item__isnull=True)
        self.stdout.write(f"Этапов без позиций заказа: {stages_without_items.count()}")
        
        # Для каждого этапа без позиции заказа пытаемся найти подходящую позицию
        for stage in stages_without_items:
            self.stdout.write(f"\nОбрабатываем этап: {stage}")
            self.stdout.write(f"  - Заказ: {stage.order}")
            
            # Ищем позиции заказа для этого заказа
            items_for_order = OrderItem.objects.filter(order=stage.order)
            self.stdout.write(f"  - Позиций для заказа: {items_for_order.count()}")
            
            if items_for_order.exists():
                # Берем первую позицию заказа
                item = items_for_order.first()
                self.stdout.write(f"  - Связываем с позицией: {item}")
                
                # Обновляем этап
                stage.order_item = item
                stage.save()
                self.stdout.write(self.style.SUCCESS("  - ✅ Этап обновлен!"))
            else:
                self.stdout.write(self.style.WARNING("  - ❌ Нет позиций заказа для этого заказа"))
        
        # Проверяем результат
        self.stdout.write(f"\n=== Результат ===")
        stages_with_items = OrderStage.objects.filter(order_item__isnull=False)
        self.stdout.write(f"Этапов с позициями заказа: {stages_with_items.count()}")
        
        tasks_with_items = EmployeeTask.objects.filter(stage__order_item__isnull=False)
        self.stdout.write(f"Задач с позициями заказа: {tasks_with_items.count()}")
        
        self.stdout.write(self.style.SUCCESS("✅ Исправление завершено!")) 