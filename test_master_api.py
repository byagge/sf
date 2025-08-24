#!/usr/bin/env python3
"""
Простой скрипт для тестирования API дашборда мастера
"""

import requests
import json

def test_master_api():
    """Тестирует API дашборда мастера"""
    
    # URL для тестирования
    base_url = "https://sf.monocode.app"  # Замените на ваш домен
    api_url = f"{base_url}/workshops/api/master/statistics/"
    
    print(f"🧪 Тестирование API дашборда мастера")
    print(f"URL: {api_url}")
    print("=" * 50)
    
    try:
        # Отправляем GET запрос без аутентификации (должен вернуть 401)
        print("1. Тест без аутентификации...")
        response = requests.get(api_url)
        print(f"   Статус: {response.status_code}")
        print(f"   Ответ: {response.text[:200]}...")
        
        if response.status_code == 401:
            print("   ✅ Правильно: требуется аутентификация")
        else:
            print(f"   ⚠️  Неожиданный статус: {response.status_code}")
        
        print()
        
        # Тест с неправильными данными аутентификации
        print("2. Тест с неправильными данными...")
        headers = {'Authorization': 'Bearer invalid_token'}
        response = requests.get(api_url, headers=headers)
        print(f"   Статус: {response.status_code}")
        print(f"   Ответ: {response.text[:200]}...")
        
        print()
        
        print("3. Тест страницы дашборда...")
        dashboard_url = f"{base_url}/workshops/master/"
        response = requests.get(dashboard_url)
        print(f"   Статус: {response.status_code}")
        
        if response.status_code == 200:
            print("   ✅ Страница загружается")
        elif response.status_code == 500:
            print("   ❌ Ошибка сервера (500)")
            print("   Это означает, что есть проблема в коде")
        else:
            print(f"   ⚠️  Неожиданный статус: {response.status_code}")
        
        print()
        
        print("4. Тест простой страницы...")
        simple_url = f"{base_url}/workshops/master/simple/"
        response = requests.get(simple_url)
        print(f"   Статус: {response.status_code}")
        
        if response.status_code == 200:
            print("   ✅ Простая страница загружается")
        elif response.status_code == 500:
            print("   ❌ Ошибка сервера (500)")
        else:
            print(f"   ⚠️  Неожиданный статус: {response.status_code}")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка сети: {e}")
    except Exception as e:
        print(f"❌ Общая ошибка: {e}")
    
    print("\n" + "=" * 50)
    print("📋 Рекомендации:")
    print("1. Если API возвращает 401 - это нормально (требуется аутентификация)")
    print("2. Если страницы возвращают 500 - есть ошибка в коде")
    print("3. Для полного тестирования нужен авторизованный пользователь с ролью 'master'")
    print("4. Проверьте логи Django для детальной информации об ошибках")

if __name__ == '__main__':
    test_master_api() 