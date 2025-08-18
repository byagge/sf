#!/usr/bin/env python
import os
import sys
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.orders.models import OrderStage, OrderItem
from apps.employee_tasks.models import EmployeeTask

def check_stages():
    print("=== Проверка этапов заказов ===")
    
    stages = OrderStage.objects.all()
    print(f"Всего этапов: {stages.count()}")
    
    for stage in stages:
        print(f"\nЭтап: {stage}")
        print(f"  - Заказ: {stage.order}")
        print(f"  - Позиция заказа: {stage.order_item}")
        print(f"  - Операция: {stage.operation}")
        print(f"  - Цех: {stage.workshop}")
        
        # Проверяем задачи для этого этапа
        tasks = EmployeeTask.objects.filter(stage=stage)
        print(f"  - Задач для этапа: {tasks.count()}")
        
        if stage.order_item:
            print(f"  - Товар в позиции: {stage.order_item.product}")
            print(f"  - Размер: {stage.order_item.size}")
            print(f"  - Цвет: {stage.order_item.color}")
        else:
            print(f"  - НЕТ ПОЗИЦИИ ЗАКАЗА!")

if __name__ == '__main__':
    check_stages() 