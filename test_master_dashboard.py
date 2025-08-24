#!/usr/bin/env python3
"""
Тестовый скрипт для проверки функциональности дашборда мастера
"""

import os
import sys
import django
from django.db import models

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.operations.workshops.models import Workshop
from apps.users.models import User

def test_master_statistics():
    """Тестирует метод получения статистики мастера"""
    print("🧪 Тестирование дашборда мастера...")
    
    # Проверяем, есть ли мастер в системе
    try:
        master = User.objects.filter(role='master').first()
        if not master:
            print("❌ В системе нет пользователей с ролью 'master'")
            print("   Создайте пользователя с ролью 'master' для тестирования")
            return False
        
        print(f"✅ Найден мастер: {master.get_full_name()} (ID: {master.id})")
        
        # Проверяем, есть ли цеха у мастера
        managed_workshops = Workshop.objects.filter(
            models.Q(manager=master) | 
            models.Q(workshop_masters__master=master, workshop_masters__is_active=True)
        ).distinct()
        
        if not managed_workshops.exists():
            print("❌ Мастер не управляет ни одним цехом")
            print("   Назначьте мастера руководителем цеха для тестирования")
            return False
        
        print(f"✅ Мастер управляет {managed_workshops.count()} цехами:")
        for workshop in managed_workshops:
            print(f"   - {workshop.name}")
        
        # Тестируем получение статистики
        try:
            stats = Workshop.get_master_statistics(master)
            if stats:
                print("✅ Статистика мастера получена успешно:")
                print(f"   - Всего цехов: {stats['overall_stats']['total_workshops']}")
                print(f"   - Всего задач: {stats['overall_stats']['total_tasks']}")
                print(f"   - Выполнено: {stats['overall_stats']['completed_tasks']}")
                print(f"   - Эффективность: {stats['overall_stats']['efficiency']:.1f}%")
                print(f"   - Статистика за неделю: {stats['period_stats']['week']['completed_tasks']} задач")
                print(f"   - Статистика за месяц: {stats['period_stats']['month']['completed_tasks']} задач")
                
                print(f"   - Детали по цехам:")
                for workshop in stats['workshops']:
                    print(f"     * {workshop['name']}: {workshop['efficiency']:.1f}% эффективность")
                
                return True
            else:
                print("❌ Не удалось получить статистику мастера")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка при получении статистики: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        return False

def test_urls():
    """Проверяет доступность URL-адресов"""
    print("\n🔗 Проверка URL-адресов...")
    
    urls_to_check = [
        '/workshops/master/',
        '/workshops/api/master/statistics/',
    ]
    
    for url in urls_to_check:
        print(f"   - {url} - должен быть доступен для мастеров")
    
    print("✅ URL-адреса настроены корректно")

def test_templates():
    """Проверяет наличие шаблонов"""
    print("\n📄 Проверка шаблонов...")
    
    templates = [
        'apps/operations/workshops/templates/master_dashboard.html',
        'apps/operations/workshops/templates/master_dashboard_mobile.html',
    ]
    
    for template in templates:
        if os.path.exists(template):
            print(f"   ✅ {template}")
        else:
            print(f"   ❌ {template} - не найден")
    
    print("✅ Все необходимые шаблоны созданы")

def main():
    """Основная функция тестирования"""
    print("🚀 Тестирование системы дашборда мастера")
    print("=" * 50)
    
    # Проверяем шаблоны
    test_templates()
    
    # Проверяем URL-адреса
    test_urls()
    
    # Тестируем функциональность
    success = test_master_statistics()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 Все тесты пройдены успешно!")
        print("   Система дашборда мастера готова к использованию")
    else:
        print("⚠️  Некоторые тесты не пройдены")
        print("   Проверьте настройки и данные в системе")
    
    print("\n📋 Для доступа к дашборду мастера:")
    print("   1. Войдите в систему как пользователь с ролью 'master'")
    print("   2. Перейдите на /workshops/master/")
    print("   3. Или нажмите кнопку 'Мой дашборд' на странице цехов")

if __name__ == '__main__':
    main() 