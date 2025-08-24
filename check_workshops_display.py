#!/usr/bin/env python3
"""
Скрипт для проверки отображения всех цехов в дашборде мастера
"""

import os
import sys
import django

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.operations.workshops.models import Workshop
from apps.users.models import User

def check_workshops_display():
    """Проверяет отображение всех цехов"""
    print("🔍 Проверка отображения цехов в дашборде мастера")
    print("=" * 60)
    
    # Проверяем всех мастеров
    masters = User.objects.filter(role='master')
    print(f"Найдено мастеров: {masters.count()}")
    
    for master in masters:
        print(f"\n👤 Мастер: {master.get_full_name()} (ID: {master.id})")
        
        # Получаем статистику мастера
        stats = Workshop.get_master_statistics(master)
        
        if stats:
            print(f"   ✅ Статистика получена")
            print(f"   📊 Всего цехов: {stats['overall_stats']['total_workshops']}")
            print(f"   📋 Всего задач: {stats['overall_stats']['total_tasks']}")
            print(f"   ✅ Выполнено: {stats['overall_stats']['completed_tasks']}")
            print(f"   📈 Эффективность: {stats['overall_stats']['efficiency']:.1f}%")
            
            print(f"\n   🏭 Цеха мастера:")
            for workshop in stats['workshops']:
                print(f"      • {workshop['name']}")
                print(f"        - Задач: {workshop['total_tasks']} (выполнено: {workshop['completed_tasks']})")
                print(f"        - Брака: {workshop['defects']}")
                print(f"        - Эффективность: {workshop['efficiency']:.1f}%")
                print(f"        - Сотрудников: {workshop['employees_count']}")
                print(f"        - Активных этапов: {workshop['active_stages']}")
        else:
            print(f"   ❌ Статистика не получена (мастер не управляет цехами)")
    
    print("\n" + "=" * 60)
    print("📋 Проверка завершена")
    print("\nДля тестирования в браузере:")
    print("1. Войти как мастер")
    print("2. Перейти на /workshops/master/")
    print("3. Проверить отображение всех цехов")
    print("4. Проверить иконки Lucide")
    print("5. Проверить статистику по каждому цеху")

def check_lucide_icons():
    """Проверяет наличие иконок Lucide в шаблонах"""
    print("\n🎨 Проверка иконок Lucide")
    print("=" * 40)
    
    templates = [
        'apps/operations/workshops/templates/master_dashboard.html',
        'apps/operations/workshops/templates/master_dashboard_mobile.html',
    ]
    
    lucide_icons = [
        'factory', 'clipboard-list', 'check-circle', 'trending-up',
        'calendar', 'calendar-days', 'alert-circle', 'refresh-cw'
    ]
    
    for template in templates:
        if os.path.exists(template):
            print(f"✅ {template}")
            with open(template, 'r', encoding='utf-8') as f:
                content = f.read()
                for icon in lucide_icons:
                    if f'data-lucide="{icon}"' in content:
                        print(f"   ✅ {icon}")
                    else:
                        print(f"   ❌ {icon} - не найден")
        else:
            print(f"❌ {template} - не найден")

if __name__ == '__main__':
    check_workshops_display()
    check_lucide_icons() 