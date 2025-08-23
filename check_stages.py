#!/usr/bin/env python
import os
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.orders.models import OrderStage, Order, OrderItem

# Check specific stages
stage_ids = [190, 191, 192]
stages = OrderStage.objects.filter(id__in=stage_ids)

print("Checking stages:")
for s in stages:
    print(f"Stage {s.id}:")
    print(f"  order: {s.order}")
    print(f"  order_item: {s.order_item}")
    if s.order:
        print(f"  order.items count: {s.order.items.count()}")
        if s.order.items.exists():
            print(f"  first order item: {s.order.items.first()}")
    print()

# Check all orders with their items
print("All orders:")
orders = Order.objects.all()
for order in orders:
    print(f"Order {order.id} ({order.name}):")
    print(f"  Items count: {order.items.count()}")
    print(f"  Stages count: {order.stages.count()}")
    if order.items.exists():
        for item in order.items.all():
            print(f"    Item {item.id}: {item.product.name if item.product else 'No product'}")
    print() 