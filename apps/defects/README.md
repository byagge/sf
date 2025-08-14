# Система управления браками (Defects)

## Обзор

Улучшенная система управления браками позволяет мастерам цехов проверять и классифицировать браки, а также создавать задачи по их восстановлению.

## Основные функции

### 1. Управление статусами браков
- **pending_master_review** - Ожидает проверки мастера
- **master_confirmed** - Подтвержден мастером
- **can_be_fixed** - Можно починить
- **sent_to_workshop** - Отправлен в цех для восстановления
- **fixed** - Исправлен
- **unrepairable** - Не подлежит восстановлению

### 2. Типы браков
- **Технический** - Штраф не списывается с сотрудника
- **Ручной** - Штраф списывается с сотрудника

### 3. Роли пользователей
- **Мастер** - Проверяет и классифицирует браки
- **Рабочий** - Исправляет браки
- **Администратор** - Видит все браки и управляет системой

## Процесс работы с браком

### Шаг 1: Проверка мастером
Мастер подходит к браку и нажимает "Проверить". Система запрашивает подтверждение того, что мастер действительно проверил брак.

### Шаг 2: Оценка возможности восстановления
Система спрашивает: "Можно ли починить брак?"

#### Если ДА (можно починить):
- Брак остается на починку
- Мастер выбирает цех для восстановления
- Создается задача "Починить браки"
- Брак переводится в статус "sent_to_workshop"

#### Если НЕТ (нельзя починить):
- Мастер выбирает тип брака:
  - **Технический** - штраф не списывается
  - **Ручной** - штраф списывается с сотрудника
- Брак переводится в статус "unrepairable"

### Шаг 3: Восстановление (если возможно)
- Брак переводится в выбранный цех
- Создается задача "Восстановление брака по заказу ID"
- Рабочий выполняет задачу
- При завершении брак отмечается как исправленный

## API Endpoints

### Браки (Defects)
- `GET /api/defects/` - Список браков
- `POST /api/defects/` - Создание брака
- `GET /api/defects/{id}/` - Детали брака
- `PUT /api/defects/{id}/` - Обновление брака
- `DELETE /api/defects/{id}/` - Удаление брака

### Действия с браками
- `POST /api/defects/{id}/confirm_by_master/` - Подтверждение мастером
- `POST /api/defects/{id}/review_defect/` - Полная проверка брака
- `POST /api/defects/{id}/mark_as_fixed/` - Отметка как исправленного

### Задачи по восстановлению (DefectRepairTask)
- `GET /api/repair-tasks/` - Список задач
- `POST /api/repair-tasks/` - Создание задачи
- `GET /api/repair-tasks/{id}/` - Детали задачи
- `PUT /api/repair-tasks/{id}/` - Обновление задачи
- `DELETE /api/repair-tasks/{id}/` - Удаление задачи

### Действия с задачами
- `POST /api/repair-tasks/{id}/start_work/` - Начать работу
- `POST /api/repair-tasks/{id}/complete_task/` - Завершить задачу

## Модели данных

### Defect (Брак)
```python
class Defect(models.Model):
    product = models.ForeignKey(Product, ...)
    user = models.ForeignKey(User, ...)  # Кто создал брак
    status = models.CharField(choices=DefectStatus.choices, ...)
    defect_type = models.CharField(choices=DefectType.choices, ...)
    can_be_fixed = models.BooleanField(...)
    target_workshop = models.ForeignKey(Workshop, ...)
    master_confirmed_by = models.ForeignKey(User, ...)
    master_confirmed_at = models.DateTimeField(...)
    fixed_at = models.DateTimeField(...)
    fixed_by = models.ForeignKey(User, ...)
    notes = models.TextField(...)
```

### DefectRepairTask (Задача по восстановлению)
```python
class DefectRepairTask(models.Model):
    defect = models.OneToOneField(Defect, ...)
    assigned_to = models.ForeignKey(User, ...)
    workshop = models.ForeignKey(Workshop, ...)
    status = models.CharField(choices=TaskStatus.choices, ...)
    title = models.CharField(...)
    description = models.TextField(...)
    priority = models.CharField(...)
    estimated_hours = models.DecimalField(...)
    actual_hours = models.DecimalField(...)
```

## Фильтрация и права доступа

### Мастер
- Видит браки только своего цеха
- Может проверять и классифицировать браки
- Управляет задачами по восстановлению в своем цехе

### Рабочий
- Видит только свои браки
- Может отмечать браки как исправленные
- Видит назначенные на него задачи по восстановлению

### Администратор
- Видит все браки и задачи
- Полный доступ к управлению

## Интерфейс

### Десктопная версия
- Полнофункциональная таблица с фильтрами
- Модальные окна для проверки браков
- Детальная статистика

### Мобильная версия
- Адаптивный дизайн для мобильных устройств
- Упрощенный интерфейс с карточками
- Модальные окна снизу экрана

## Установка и настройка

1. Применить миграции:
```bash
python manage.py makemigrations defects
python manage.py migrate
```

2. Настроить права доступа в админ-панели

3. Убедиться, что у пользователей правильно установлены роли и цехи

## Примеры использования

### Создание брака
```python
defect = Defect.objects.create(
    product=product,
    user=worker,
    status=Defect.DefectStatus.PENDING_MASTER_REVIEW
)
```

### Проверка брака мастером
```python
# Подтверждение проверки
defect.confirm_by_master(master_user)

# Установка возможности восстановления
defect.set_repairability(True)

# Отправка в цех
defect.send_to_workshop(target_workshop)
```

### Создание задачи по восстановлению
```python
task = DefectRepairTask.objects.create(
    defect=defect,
    workshop=target_workshop,
    title=f"Восстановление брака по заказу {order_id}",
    priority='medium'
)
```

## Логирование и аудит

Система автоматически отслеживает:
- Кто и когда подтвердил брак
- Кто и когда исправил брак
- Время выполнения задач
- Изменения статусов

## Уведомления

При изменении статуса брака система может отправлять уведомления:
- Мастеру о новых браках для проверки
- Рабочему о назначенных задачах
- Администратору о критических изменениях 