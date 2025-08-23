# Руководство по развертыванию Smart Factory на Ubuntu сервере

## 📋 Требования к серверу

### Минимальные требования:
- **ОС**: Ubuntu 20.04 LTS или новее
- **RAM**: 4 GB (рекомендуется 8 GB)
- **CPU**: 2 ядра (рекомендуется 4 ядра)
- **Диск**: 20 GB свободного места
- **Сеть**: Статический IP адрес

### Рекомендуемые требования:
- **RAM**: 8-16 GB
- **CPU**: 4-8 ядер
- **Диск**: SSD 50+ GB
- **Сеть**: Высокоскоростное подключение

## 🚀 Пошаговая установка

### 1. Подготовка сервера

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка необходимых пакетов
sudo apt install -y python3 python3-pip python3-venv git nginx postgresql postgresql-contrib redis-server supervisor curl wget unzip

# Создание пользователя для приложения
sudo adduser smartfactory --disabled-password --gecos ""
sudo usermod -aG sudo smartfactory
```

### 2. Настройка PostgreSQL

```bash
# Переключение на пользователя postgres
sudo -u postgres psql

# Создание базы данных и пользователя
CREATE DATABASE smart_factory;
CREATE USER smart_factory_user WITH PASSWORD 'your_secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE smart_factory TO smart_factory_user;
ALTER USER smart_factory_user CREATEDB;
\q

# Оптимизация PostgreSQL
sudo nano /etc/postgresql/*/main/postgresql.conf
```

Добавьте в конец файла:
```conf
# Оптимизация для производительности
max_connections = 200
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
```

```bash
# Перезапуск PostgreSQL
sudo systemctl restart postgresql
sudo systemctl enable postgresql
```

### 3. Настройка Redis

```bash
# Редактирование конфигурации Redis
sudo nano /etc/redis/redis.conf
```

Найдите и измените следующие параметры:
```conf
# Память
maxmemory 512mb
maxmemory-policy allkeys-lru

# Сохранение
save 900 1
save 300 10
save 60 10000

# Безопасность
bind 127.0.0.1
protected-mode yes
```

```bash
# Перезапуск Redis
sudo systemctl restart redis-server
sudo systemctl enable redis-server
```

### 4. Клонирование проекта

```bash
# Переключение на пользователя приложения
sudo su - smartfactory

# Клонирование проекта
git clone https://github.com/your-repo/smart-factory.git
cd smart-factory

# Создание виртуального окружения
python3 -m venv venv
source venv/bin/activate
```

### 5. Установка зависимостей

```bash
# Обновление pip
pip install --upgrade pip

# Установка production зависимостей
pip install -r requirements_production.txt

# Установка дополнительных пакетов для мониторинга
pip install psutil django-cacheops django-query-profiler
```

### 6. Настройка переменных окружения

```bash
# Создание .env файла
cat > .env << EOF
DJANGO_SETTINGS_MODULE=core.settings_production
DJANGO_SECRET_KEY=your_super_secret_key_here_change_this
DB_NAME=smart_factory
DB_USER=smart_factory_user
DB_PASSWORD=your_secure_password_here
DB_HOST=localhost
DB_PORT=5432
REDIS_URL=redis://127.0.0.1:6379
EMAIL_HOST=localhost
EMAIL_PORT=587
EMAIL_USE_TLS=False
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
EOF

# Установка прав на .env файл
chmod 600 .env
```

### 7. Настройка Django

```bash
# Применение миграций
python manage.py migrate

# Создание суперпользователя
python manage.py createsuperuser

# Сбор статических файлов
python manage.py collectstatic --noinput

# Создание папки для логов
mkdir -p logs
chmod 755 logs
```

### 8. Настройка Gunicorn

```bash
# Создание конфигурации systemd для Gunicorn
sudo nano /etc/systemd/system/smartfactory.service
```

Содержимое файла:
```ini
[Unit]
Description=Smart Factory Gunicorn daemon
After=network.target

[Service]
User=smartfactory
Group=smartfactory
WorkingDirectory=/home/smartfactory/smart-factory
Environment="PATH=/home/smartfactory/smart-factory/venv/bin"
Environment="DJANGO_SETTINGS_MODULE=core.settings_production"
ExecStart=/home/smartfactory/smart-factory/venv/bin/gunicorn --config gunicorn.conf.py core.wsgi:application
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

```bash
# Активация и запуск сервиса
sudo systemctl daemon-reload
sudo systemctl start smartfactory
sudo systemctl enable smartfactory
```

### 9. Настройка Celery

```bash
# Создание конфигурации для Celery worker
sudo nano /etc/systemd/system/smartfactory-celery.service
```

Содержимое файла:
```ini
[Unit]
Description=Smart Factory Celery Worker
After=network.target

[Service]
Type=forking
User=smartfactory
Group=smartfactory
WorkingDirectory=/home/smartfactory/smart-factory
Environment="PATH=/home/smartfactory/smart-factory/venv/bin"
Environment="DJANGO_SETTINGS_MODULE=core.settings_production"
ExecStart=/home/smartfactory/smart-factory/venv/bin/celery multi start worker1 -A core -l info
ExecStop=/home/smartfactory/smart-factory/venv/bin/celery multi stopwait worker1 -A core
ExecReload=/home/smartfactory/smart-factory/venv/bin/celery multi restart worker1 -A core -l info

[Install]
WantedBy=multi-user.target
```

```bash
# Создание конфигурации для Celery beat
sudo nano /etc/systemd/system/smartfactory-celerybeat.service
```

Содержимое файла:
```ini
[Unit]
Description=Smart Factory Celery Beat
After=network.target

[Service]
Type=simple
User=smartfactory
Group=smartfactory
WorkingDirectory=/home/smartfactory/smart-factory
Environment="PATH=/home/smartfactory/smart-factory/venv/bin"
Environment="DJANGO_SETTINGS_MODULE=core.settings_production"
ExecStart=/home/smartfactory/smart-factory/venv/bin/celery -A core beat -l info
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Активация и запуск Celery сервисов
sudo systemctl daemon-reload
sudo systemctl start smartfactory-celery
sudo systemctl enable smartfactory-celery
sudo systemctl start smartfactory-celerybeat
sudo systemctl enable smartfactory-celerybeat
```

### 10. Настройка Nginx

```bash
# Создание конфигурации Nginx
sudo nano /etc/nginx/sites-available/smartfactory
```

Содержимое файла:
```nginx
server {
    listen 80;
    server_name your_server_ip_here;  # Замените на ваш IP адрес

    # Размер загружаемых файлов
    client_max_body_size 10M;

    # Статические файлы
    location /static/ {
        alias /home/smartfactory/smart-factory/staticfiles/;
        expires 1y;
        add_header Cache-Control "public, immutable";
        access_log off;
    }

    # Медиа файлы
    location /media/ {
        alias /home/smartfactory/smart-factory/media/;
        expires 1y;
        add_header Cache-Control "public";
        access_log off;
    }

    # Основное приложение
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }

    # Health check
    location /health/ {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
```

```bash
# Активация сайта
sudo ln -s /etc/nginx/sites-available/smartfactory /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default  # Удаляем дефолтный сайт

# Проверка конфигурации Nginx
sudo nginx -t

# Перезапуск Nginx
sudo systemctl restart nginx
sudo systemctl enable nginx
```

### 11. Настройка файрвола

```bash
# Установка UFW
sudo apt install ufw

# Настройка правил
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp  # Для будущего SSL

# Активация файрвола
sudo ufw enable
```

### 12. Запуск оптимизации

```bash
# Переключение на пользователя приложения
sudo su - smartfactory
cd smart-factory
source venv/bin/activate

# Запуск автоматической оптимизации
python scripts/optimize_system.py
```

## 🔧 Управление сервисами

### Проверка статуса сервисов:
```bash
sudo systemctl status smartfactory
sudo systemctl status smartfactory-celery
sudo systemctl status smartfactory-celerybeat
sudo systemctl status nginx
sudo systemctl status postgresql
sudo systemctl status redis-server
```

### Перезапуск сервисов:
```bash
sudo systemctl restart smartfactory
sudo systemctl restart smartfactory-celery
sudo systemctl restart smartfactory-celerybeat
sudo systemctl restart nginx
```

### Просмотр логов:
```bash
# Логи приложения
sudo journalctl -u smartfactory -f

# Логи Celery
sudo journalctl -u smartfactory-celery -f
sudo journalctl -u smartfactory-celerybeat -f

# Логи Nginx
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# Логи PostgreSQL
sudo tail -f /var/log/postgresql/postgresql-*.log
```

## 📊 Мониторинг

### Создание скрипта мониторинга:
```bash
sudo nano /home/smartfactory/monitor.sh
```

Содержимое:
```bash
#!/bin/bash
echo "=== Smart Factory System Status ==="
echo "Date: $(date)"
echo ""

echo "=== Service Status ==="
systemctl is-active smartfactory
systemctl is-active smartfactory-celery
systemctl is-active smartfactory-celerybeat
systemctl is-active nginx
systemctl is-active postgresql
systemctl is-active redis-server

echo ""
echo "=== System Resources ==="
free -h
df -h /
top -bn1 | grep "Cpu(s)"

echo ""
echo "=== Application Logs ==="
tail -n 10 /home/smartfactory/smart-factory/logs/django.log
```

```bash
# Установка прав на выполнение
chmod +x /home/smartfactory/monitor.sh
```

### Настройка автоматического мониторинга:
```bash
# Добавление в crontab
crontab -e

# Добавить строку для ежедневного мониторинга в 9:00
0 9 * * * /home/smartfactory/monitor.sh >> /home/smartfactory/monitoring.log 2>&1
```

## 🔒 Безопасность

### Обновление системы:
```bash
# Автоматические обновления безопасности
sudo apt install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

### Резервное копирование:
```bash
# Создание скрипта резервного копирования
sudo nano /home/smartfactory/backup.sh
```

Содержимое:
```bash
#!/bin/bash
BACKUP_DIR="/home/smartfactory/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Резервное копирование базы данных
pg_dump smart_factory > $BACKUP_DIR/db_backup_$DATE.sql

# Резервное копирование медиа файлов
tar -czf $BACKUP_DIR/media_backup_$DATE.tar.gz media/

# Удаление старых резервных копий (старше 7 дней)
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
```

```bash
# Установка прав и добавление в crontab
chmod +x /home/smartfactory/backup.sh
crontab -e

# Добавить строку для ежедневного резервного копирования в 2:00
0 2 * * * /home/smartfactory/backup.sh
```

## 🚀 Проверка установки

### Тестирование приложения:
```bash
# Проверка доступности сайта
curl -I http://your_server_ip_here

# Проверка health check
curl http://your_server_ip_here/health/

# Проверка статических файлов
curl -I http://your_server_ip_here/static/admin/css/base.css
```

### Проверка производительности:
```bash
# Тест нагрузки (установите apache2-utils)
sudo apt install apache2-utils
ab -n 1000 -c 10 http://your_server_ip_here/
```

## 📝 Полезные команды

### Управление проектом:
```bash
# Обновление кода
cd /home/smartfactory/smart-factory
git pull
source venv/bin/activate
pip install -r requirements_production.txt
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart smartfactory

# Очистка кэша
redis-cli FLUSHALL

# Очистка сессий
python manage.py clearsessions
```

### Мониторинг производительности:
```bash
# Просмотр активных соединений PostgreSQL
sudo -u postgres psql -c "SELECT count(*) FROM pg_stat_activity;"

# Просмотр статистики Redis
redis-cli info memory
redis-cli info stats

# Просмотр логов производительности
tail -f /home/smartfactory/smart-factory/logs/optimization.log
```

## 🎯 Готово!

Ваш Smart Factory теперь развернут и оптимизирован на Ubuntu сервере. Система готова к работе под высокими нагрузками с автоматическим мониторингом и резервным копированием.

**Доступ к приложению**: http://your_server_ip_here
**Админ панель**: http://your_server_ip_here/admin/

Не забудьте:
1. Заменить `your_server_ip_here` на реальный IP адрес сервера
2. Изменить пароли в .env файле
3. Настроить SSL сертификат в будущем для production
4. Регулярно проверять логи и метрики производительности 