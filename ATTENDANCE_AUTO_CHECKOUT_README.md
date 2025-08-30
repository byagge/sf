# Автоматическая отметка ухода сотрудников

## Описание

Система автоматической отметки ухода сотрудников после 18:00 с отображением статуса присутствия в мобильных интерфейсах.

## Функциональность

### 1. Автоматическая отметка ухода
- **Время срабатывания**: После 18:00 (18:00)
- **Логика**: Все сотрудники, которые пришли на работу, но не отметили уход, автоматически отмечаются как ушедшие
- **Способы запуска**:
  - Автоматически через Celery Beat (каждый час)
  - Вручную через API endpoint
  - Через management command
  - Через кнопку в мобильном интерфейсе

### 2. Отображение статуса присутствия
- **Статусы**:
  - 🟢 **На работе** (present) - сотрудник пришел, но не ушел
  - ⚪ **Ушел** (checked_out) - сотрудник отметил уход
  - 🔴 **Не пришел** (absent) - сотрудник не отмечался сегодня

### 3. Визуальные индикаторы
- Цветные точки на аватарах сотрудников
- Текстовые статусы под именами
- Кнопка автоматической отметки ухода в header

## API Endpoints

### 1. Получение статуса всех сотрудников
```
GET /attendance/api/employee-status/
```

**Ответ:**
```json
{
  "date": "2024-01-15",
  "current_time": "2024-01-15T14:30:00Z",
  "employees": [
    {
      "id": 1,
      "name": "Иван Иванов",
      "status": "present",
      "check_in_time": "2024-01-15T09:00:00Z",
      "check_out_time": null,
      "is_late": false,
      "penalty_amount": 0.0
    }
  ]
}
```

### 2. Получение статуса по цеху
```
GET /attendance/api/employee-status-by-workshop/?workshop_id=1
```

### 3. Автоматическая отметка ухода
```
POST /attendance/api/auto-checkout/
```

**Ответ:**
```json
{
  "success": true,
  "message": "Автоматически отмечен уход для 5 сотрудников",
  "checked_out_count": 5,
  "checkout_time": "2024-01-15T18:00:00Z"
}
```

## Management Commands

### Автоматическая отметка ухода
```bash
python manage.py auto_checkout_after_6pm
```

**Флаги:**
- `--force` - принудительно выполнить независимо от времени

### Примеры использования:
```bash
# Обычный запуск (только после 18:00)
python manage.py auto_checkout_after_6pm

# Принудительный запуск
python manage.py auto_checkout_after_6pm --force
```

## Celery Tasks

### Периодические задачи
- `auto_checkout_after_6pm` - выполняется каждый час, проверяет время и отмечает уход
- `cleanup_old_attendance_records` - очищает записи старше 1 года (еженедельно)

### Ручной запуск задач
```python
from apps.attendance.tasks import auto_checkout_after_6pm

# Запуск задачи
result = auto_checkout_after_6pm.delay()
print(result.get())
```

## Мобильные интерфейсы

### Обновления в шаблонах:
1. **employees_mobile_master.html** - для мастеров цехов
2. **employees_mobile.html** - для обычных пользователей

### Новые элементы:
- Цветные индикаторы статуса на аватарах
- Текстовые статусы под именами
- Кнопка автоматической отметки ухода в header

## Тестирование

### Тестовый скрипт
```bash
python test_auto_checkout.py
```

Скрипт проверяет:
- Текущий статус сотрудников
- Возможность автоматической отметки ухода
- Статистику посещаемости

### Ручное тестирование API
```bash
# Получить статус сотрудников
curl -X GET "http://localhost:8000/attendance/api/employee-status/" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Автоматическая отметка ухода
curl -X POST "http://localhost:8000/attendance/api/auto-checkout/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "X-CSRFToken: YOUR_CSRF_TOKEN"
```

## Настройка

### 1. Время автоматической отметки
Измените время в файлах:
- `apps/attendance/views.py` - функция `auto_checkout_after_6pm`
- `apps/attendance/tasks.py` - задача `auto_checkout_after_6pm`
- `apps/attendance/management/commands/auto_checkout_after_6pm.py`

### 2. Периодичность выполнения
Настройте в `core/celery.py`:
```python
'auto-checkout-after-6pm': {
    'task': 'apps.attendance.tasks.auto_checkout_after_6pm',
    'schedule': 3600.0,  # Каждый час
},
```

### 3. Штрафы за опоздание
Настройте в `apps/attendance/models.py`:
```python
def calculate_penalty(self):
    work_start_time = time(9, 0)  # Время начала работы
    # Штраф 500 сомов за опоздание
    self.penalty_amount = 500.00
```

## Мониторинг

### Логи
Проверяйте логи Celery для мониторинга выполнения задач:
```bash
celery -A core worker -l info
celery -A core beat -l info
```

### Статистика
API endpoint `/attendance/api/overview/` предоставляет статистику:
- Количество присутствующих сегодня
- Количество ушедших
- Количество опозданий
- Общая сумма штрафов

## Безопасность

- Все API endpoints требуют аутентификации
- CSRF защита для POST запросов
- Проверка времени для предотвращения преждевременной отметки ухода
- Логирование всех операций

## Устранение неполадок

### Проблема: Задача не выполняется
1. Проверьте, запущен ли Celery Beat
2. Проверьте логи Celery
3. Убедитесь, что время сервера корректное

### Проблема: Статус не обновляется
1. Проверьте API endpoint `/attendance/api/employee-status/`
2. Обновите страницу в браузере
3. Проверьте консоль браузера на ошибки

### Проблема: Кнопка не работает
1. Проверьте CSRF токен
2. Убедитесь, что пользователь аутентифицирован
3. Проверьте права доступа пользователя 