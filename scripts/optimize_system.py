#!/usr/bin/env python3
"""
Автоматический скрипт оптимизации системы Smart Factory
Запускает все оптимизации и проверяет производительность
"""

import os
import sys
import django
import time
import logging
from pathlib import Path

# Добавляем корневую директорию проекта в Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings_production')
django.setup()

from django.core.management import execute_from_command_line
from django.conf import settings
from django.core.cache import cache
from django.db import connection

# Импорт модулей оптимизации
from core.database import DatabaseOptimizer, DatabaseMaintenance, optimize_database_settings
from core.cache_manager import optimize_cache, CacheOptimizer
from core.session_manager import optimize_sessions, cleanup_old_sessions
from core.monitoring import get_performance_summary, log_performance_metrics

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(project_root / 'logs' / 'optimization.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def run_database_optimization():
    """Оптимизация базы данных"""
    logger.info("Начинаем оптимизацию базы данных...")
    
    try:
        # Применяем настройки оптимизации
        optimize_database_settings()
        
        # Оптимизируем соединения
        DatabaseOptimizer.optimize_connections()
        
        # Обновляем статистику
        DatabaseMaintenance.update_statistics()
        
        # Очищаем старые данные
        DatabaseMaintenance.cleanup_old_data()
        
        logger.info("Оптимизация базы данных завершена успешно")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при оптимизации базы данных: {e}")
        return False


def run_cache_optimization():
    """Оптимизация кэша"""
    logger.info("Начинаем оптимизацию кэша...")
    
    try:
        # Оптимизируем настройки кэша
        CacheOptimizer.optimize_cache_settings()
        
        # Разогреваем кэш
        CacheOptimizer.warm_cache()
        
        # Очищаем устаревшие данные
        CacheOptimizer.cleanup_expired_cache()
        
        logger.info("Оптимизация кэша завершена успешно")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при оптимизации кэша: {e}")
        return False


def run_session_optimization():
    """Оптимизация сессий"""
    logger.info("Начинаем оптимизацию сессий...")
    
    try:
        # Оптимизируем сессии
        optimize_sessions()
        
        # Очищаем старые сессии
        cleanup_old_sessions()
        
        logger.info("Оптимизация сессий завершена успешно")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при оптимизации сессий: {e}")
        return False


def run_static_files_optimization():
    """Оптимизация статических файлов"""
    logger.info("Начинаем оптимизацию статических файлов...")
    
    try:
        # Собираем статические файлы
        execute_from_command_line(['manage.py', 'collectstatic', '--noinput'])
        
        # Сжимаем статические файлы
        execute_from_command_line(['manage.py', 'compress', '--force'])
        
        logger.info("Оптимизация статических файлов завершена успешно")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при оптимизации статических файлов: {e}")
        return False


def run_migrations():
    """Запуск миграций"""
    logger.info("Запускаем миграции...")
    
    try:
        # Применяем миграции
        execute_from_command_line(['manage.py', 'migrate', '--noinput'])
        
        logger.info("Миграции применены успешно")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при применении миграций: {e}")
        return False


def check_system_health():
    """Проверка состояния системы"""
    logger.info("Проверяем состояние системы...")
    
    try:
        # Получаем сводку производительности
        summary = get_performance_summary()
        
        # Проверяем ключевые метрики
        system_stats = summary.get('system', {})
        health_report = summary.get('health', {})
        
        # Логируем результаты
        logger.info(f"CPU использование: {system_stats.get('cpu_percent', 0)}%")
        logger.info(f"Использование памяти: {system_stats.get('memory_percent', 0)}%")
        logger.info(f"Использование диска: {system_stats.get('disk_percent', 0)}%")
        
        # Проверяем здоровье системы
        db_health = health_report.get('database', {}).get('status', 'unknown')
        cache_health = health_report.get('cache', {}).get('status', 'unknown')
        system_health = health_report.get('system', {}).get('status', 'unknown')
        
        logger.info(f"Состояние БД: {db_health}")
        logger.info(f"Состояние кэша: {cache_health}")
        logger.info(f"Состояние системы: {system_health}")
        
        # Проверяем наличие предупреждений
        alerts = summary.get('alerts', [])
        if alerts:
            logger.warning(f"Найдено {len(alerts)} предупреждений:")
            for alert in alerts:
                logger.warning(f"  - {alert['message']}")
        
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при проверке состояния системы: {e}")
        return False


def run_performance_tests():
    """Запуск тестов производительности"""
    logger.info("Запускаем тесты производительности...")
    
    try:
        # Тест подключения к БД
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            logger.info("Тест подключения к БД: УСПЕШНО")
        
        # Тест кэша
        test_key = 'performance_test'
        cache.set(test_key, 'test_value', 60)
        result = cache.get(test_key)
        cache.delete(test_key)
        
        if result == 'test_value':
            logger.info("Тест кэша: УСПЕШНО")
        else:
            logger.error("Тест кэша: ОШИБКА")
        
        # Тест производительности запросов
        from apps.users.models import User
        
        start_time = time.time()
        user_count = User.objects.count()
        query_time = time.time() - start_time
        
        logger.info(f"Тест запросов: {user_count} пользователей за {query_time:.3f}с")
        
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при тестировании производительности: {e}")
        return False


def create_optimization_report():
    """Создание отчета об оптимизации"""
    logger.info("Создаем отчет об оптимизации...")
    
    try:
        summary = get_performance_summary()
        
        report = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'optimization_results': {
                'database': True,
                'cache': True,
                'sessions': True,
                'static_files': True,
                'migrations': True,
            },
            'performance_metrics': summary,
            'recommendations': []
        }
        
        # Анализируем метрики и даем рекомендации
        system_stats = summary.get('system', {})
        
        if system_stats.get('cpu_percent', 0) > 80:
            report['recommendations'].append("Высокое использование CPU - рассмотрите возможность масштабирования")
        
        if system_stats.get('memory_percent', 0) > 85:
            report['recommendations'].append("Высокое использование памяти - увеличьте RAM или оптимизируйте кэш")
        
        if system_stats.get('disk_percent', 0) > 90:
            report['recommendations'].append("Высокое использование диска - очистите старые файлы или увеличьте дисковое пространство")
        
        # Сохраняем отчет
        report_path = project_root / 'logs' / 'optimization_report.json'
        import json
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"Отчет сохранен в {report_path}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при создании отчета: {e}")
        return False


def main():
    """Основная функция оптимизации"""
    logger.info("=" * 60)
    logger.info("ЗАПУСК АВТОМАТИЧЕСКОЙ ОПТИМИЗАЦИИ СИСТЕМЫ")
    logger.info("=" * 60)
    
    # Создаем папку для логов если её нет
    logs_dir = project_root / 'logs'
    logs_dir.mkdir(exist_ok=True)
    
    start_time = time.time()
    
    # Выполняем оптимизации
    optimizations = [
        ("Миграции", run_migrations),
        ("База данных", run_database_optimization),
        ("Кэш", run_cache_optimization),
        ("Сессии", run_session_optimization),
        ("Статические файлы", run_static_files_optimization),
    ]
    
    results = {}
    
    for name, func in optimizations:
        logger.info(f"\n--- {name.upper()} ---")
        results[name] = func()
    
    # Проверяем состояние системы
    logger.info("\n--- ПРОВЕРКА СОСТОЯНИЯ СИСТЕМЫ ---")
    check_system_health()
    
    # Запускаем тесты производительности
    logger.info("\n--- ТЕСТЫ ПРОИЗВОДИТЕЛЬНОСТИ ---")
    run_performance_tests()
    
    # Создаем отчет
    logger.info("\n--- СОЗДАНИЕ ОТЧЕТА ---")
    create_optimization_report()
    
    # Итоговая сводка
    total_time = time.time() - start_time
    
    logger.info("\n" + "=" * 60)
    logger.info("ИТОГИ ОПТИМИЗАЦИИ")
    logger.info("=" * 60)
    
    for name, success in results.items():
        status = "УСПЕШНО" if success else "ОШИБКА"
        logger.info(f"{name}: {status}")
    
    logger.info(f"Общее время выполнения: {total_time:.2f} секунд")
    
    # Проверяем общий результат
    all_success = all(results.values())
    
    if all_success:
        logger.info("Все оптимизации выполнены успешно!")
        return 0
    else:
        logger.error("Некоторые оптимизации завершились с ошибками!")
        return 1


if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Оптимизация прервана пользователем")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        sys.exit(1) 