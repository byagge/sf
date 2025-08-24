# Развертывание системы дашборда мастера

## Описание проблемы

В продакшене возникает ошибка 500 при обращении к `/workshops/master/`:
```
Aug 24 15:36:53 vm3525102.firstbyte.club gunicorn[51330]: 127.0.0.1 - - [24/Aug/2025:21:36:53 +0600] "GET /workshops/master/ HTTP/1.0" 500 145
```

## Причины ошибки

1. **Неправильные импорты** - использование `models.F` вместо `F`
2. **Неправильные связи моделей** - попытка доступа к несуществующим полям
3. **Отсутствие обработки ошибок** - необработанные исключения приводят к 500 ошибке

## Исправления

### 1. Модель Workshop (models.py)

✅ **Исправлено:**
- Добавлен правильный импорт `from django.db.models import F`
- Исправлена логика подсчета брака через `employee_task__stage__workshop`
- Добавлен импорт `User` для подсчета сотрудников
- Исправлены все обращения к полям моделей

### 2. Представления (views.py)

✅ **Исправлено:**
- Добавлена проверка существования атрибута `role` у пользователя
- Добавлено логирование для отладки
- Добавлена обработка исключений с try-catch
- Создано простое представление для тестирования

### 3. URL-маршруты (urls.py)

✅ **Добавлено:**
- `/workshops/master/` - основной дашборд
- `/workshops/master/simple/` - тестовая страница
- `/workshops/api/master/statistics/` - API статистики

### 4. Шаблоны

✅ **Создано:**
- `master_dashboard.html` - десктопная версия
- `master_dashboard_mobile.html` - мобильная версия  
- `master_dashboard_simple.html` - тестовая версия

## Инструкции по развертыванию

### Шаг 1: Обновление кода

```bash
# Остановить сервис
sudo systemctl stop gunicorn

# Обновить файлы
git pull origin main

# Применить миграции (если есть)
python manage.py migrate

# Проверить синтаксис
python manage.py check

# Запустить сервис
sudo systemctl start gunicorn
```

### Шаг 2: Проверка логов

```bash
# Логи gunicorn
sudo journalctl -u gunicorn -f

# Логи Django (если настроены)
tail -f /var/log/django/error.log
```

### Шаг 3: Тестирование

1. **Тест API без аутентификации:**
   ```bash
   curl -i https://sf.monocode.app/workshops/api/master/statistics/
   # Должен вернуть 401 (Unauthorized)
   ```

2. **Тест страницы дашборда:**
   ```bash
   curl -i https://sf.monocode.app/workshops/master/
   # Должен вернуть 200 или 302 (redirect на login)
   ```

3. **Тест простой страницы:**
   ```bash
   curl -i https://sf.monocode.app/workshops/master/simple/
   # Должен вернуть 200 или 302 (redirect на login)
   ```

### Шаг 4: Проверка в браузере

1. Войти в систему как пользователь с ролью `master`
2. Перейти на `/workshops/master/`
3. Проверить загрузку статистики
4. Проверить мобильную версию

## Отладка

### Если ошибка 500 все еще возникает:

1. **Проверить логи Django:**
   ```python
   # В settings.py добавить
   LOGGING = {
       'version': 1,
       'disable_existing_loggers': False,
       'handlers': {
           'file': {
               'level': 'DEBUG',
               'class': 'logging.FileHandler',
               'filename': '/var/log/django/debug.log',
           },
       },
       'loggers': {
           'apps.operations.workshops': {
               'handlers': ['file'],
               'level': 'DEBUG',
               'propagate': True,
           },
       },
   }
   ```

2. **Проверить простую страницу:**
   - Перейти на `/workshops/master/simple/`
   - Эта страница показывает детальную информацию об ошибках

3. **Проверить права доступа:**
   ```python
   # В Django shell
   from apps.users.models import User
   from apps.operations.workshops.models import Workshop
   
   # Найти мастера
   master = User.objects.filter(role='master').first()
   print(f"Мастер: {master}")
   
   # Проверить цеха мастера
   workshops = Workshop.objects.filter(
       models.Q(manager=master) | 
       models.Q(workshop_masters__master=master, workshop_masters__is_active=True)
   )
   print(f"Цеха мастера: {list(workshops.values('id', 'name'))}")
   ```

## Структура файлов

```
apps/operations/workshops/
├── models.py                    # ✅ Исправлена модель Workshop
├── views.py                     # ✅ Добавлены представления
├── urls.py                      # ✅ Добавлены URL-маршруты
└── templates/
    ├── master_dashboard.html           # ✅ Десктопная версия
    ├── master_dashboard_mobile.html    # ✅ Мобильная версия
    └── master_dashboard_simple.html    # ✅ Тестовая версия
```

## Проверка работоспособности

После развертывания система должна:

1. ✅ Не возвращать ошибку 500
2. ✅ Показывать дашборд для мастеров
3. ✅ Отображать статистику по цехам
4. ✅ Работать на мобильных устройствах
5. ✅ Предоставлять API для получения статистики

## Мониторинг

Добавить в мониторинг проверку:
- HTTP статус `/workshops/master/` (должен быть 200 или 302)
- HTTP статус `/workshops/api/master/statistics/` (должен быть 401 для неавторизованных)
- Логи Django на наличие ошибок

## Контакты

При возникновении проблем:
1. Проверить логи Django и gunicorn
2. Использовать тестовую страницу `/workshops/master/simple/`
3. Проверить права доступа пользователя
4. Убедиться, что все импорты корректны 