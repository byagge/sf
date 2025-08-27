#!/usr/bin/env python
"""
Тестовый скрипт для проверки системы услуг мастера
"""

import os
import sys
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.services.models import Service
from apps.operations.workshops.models import Workshop
from apps.inventory.models import RawMaterial

def test_services_master():
    print("=== Тестирование системы услуг мастера ===\n")
    
    # Проверяем наличие цехов
    workshops = Workshop.objects.all()
    print(f"Найдено цехов: {workshops.count()}")
    for workshop in workshops[:5]:  # Показываем первые 5
        print(f"  - {workshop.id}: {workshop.name}")
    
    # Проверяем наличие услуг
    services = Service.objects.all()
    print(f"\nНайдено услуг: {services.count()}")
    
    if services.count() == 0:
        print("Создаем тестовые услуги...")
        
        # Создаем тестовые услуги для каждого цеха
        for workshop in workshops[:3]:  # Первые 3 цеха
            service = Service.objects.create(
                name=f"Тестовая услуга {workshop.name}",
                description=f"Описание тестовой услуги для цеха {workshop.name}",
                unit="шт",
                workshop=workshop,
                service_price=100.00,
                defect_penalty=50.00,
                is_active=True
            )
            print(f"  Создана услуга: {service.name} (цена: {service.service_price} ₽)")
    
    # Показываем услуги по цехам
    print("\n=== Услуги по цехам ===")
    for workshop in workshops[:3]:
        workshop_services = Service.objects.filter(workshop=workshop, is_active=True)
        print(f"\nЦех: {workshop.name}")
        if workshop_services.exists():
            for service in workshop_services:
                print(f"  - {service.name}: {service.service_price} ₽")
        else:
            print("  Нет активных услуг")
    
    print("\n=== API Endpoints для тестирования ===")
    print("1. Получение цехов: GET /services/api/master/workshops/")
    print("2. Получение услуг по цеху: GET /services/api/master/services/?workshop=1")
    print("3. Обновление цены: PATCH /services/api/master/services/1/update-price/")
    print("4. Страница мастера: /services/master/")
    
    print("\n=== Тест завершен ===")

if __name__ == "__main__":
    test_services_master() 