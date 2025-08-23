from django.core.management.base import BaseCommand
from apps.orders.models import OrderStage, OrderItem

class Command(BaseCommand):
    help = 'Fix stages that have null order_item by linking them to appropriate order items'

    def handle(self, *args, **options):
        # Find stages with null order_item
        null_stages = OrderStage.objects.filter(order_item__isnull=True)
        
        self.stdout.write(f"Found {null_stages.count()} stages with null order_item")
        
        fixed_count = 0
        deleted_count = 0
        
        for stage in null_stages:
            if not stage.order:
                # If stage has no order, delete it
                stage.delete()
                deleted_count += 1
                self.stdout.write(f"Deleted stage {stage.id} (no order)")
                continue
            
            # Find order items for this order
            order_items = stage.order.items.all()
            
            if not order_items.exists():
                # If order has no items, delete the stage
                stage.delete()
                deleted_count += 1
                self.stdout.write(f"Deleted stage {stage.id} (order {stage.order.id} has no items)")
                continue
            
            # Link stage to the first order item
            first_item = order_items.first()
            stage.order_item = first_item
            stage.plan_quantity = first_item.quantity
            stage.save()
            fixed_count += 1
            
            self.stdout.write(f"Fixed stage {stage.id}: linked to order_item {first_item.id}")
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully fixed {fixed_count} stages, deleted {deleted_count} invalid stages'
            )
        ) 