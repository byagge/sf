#!/usr/bin/env python
"""
Тестовый скрипт для проверки логики расчета штрафов
"""

from datetime import datetime, time

def test_penalty_logic():
    """Тестирует логику расчета штрафов"""
    
    print("🧪 Тестирование логики расчета штрафов...")
    
    # Тестовые случаи
    test_cases = [
        ("08:30", "До 9:00 - без штрафа"),
        ("08:59", "До 9:00 - без штрафа"),
        ("09:00", "Ровно 9:00 - без штрафа"),
        ("09:01", "После 9:00 - штраф 500"),
        ("09:15", "После 9:00 - штраф 500"),
        ("10:00", "После 9:00 - штраф 500"),
        ("12:00", "После 9:00 - штраф 500"),
    ]
    
    work_start_time = time(9, 0)
    
    for time_str, description in test_cases:
        # Парсим время
        hour, minute = map(int, time_str.split(':'))
        check_in_time = time(hour, minute)
        
        # Проверяем логику
        is_late = check_in_time > work_start_time
        penalty = 500.00 if is_late else 0.00
        
        status = "🚨 ШТРАФ" if is_late else "✅ БЕЗ ШТРАФА"
        
        print(f"{time_str:>5} → {status:>15} ({penalty:>6.2f} сомов) - {description}")
    
    print("\n📋 Логика работы:")
    print("• Время < 9:00:00 → Без штрафа (0.00 сомов)")
    print("• Время = 9:00:00 → Без штрафа (0.00 сомов)")
    print("• Время > 9:00:00 → Штраф (500.00 сомов)")

if __name__ == "__main__":
    test_penalty_logic() 