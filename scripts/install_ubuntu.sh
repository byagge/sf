#!/bin/bash

# Автоматический скрипт установки Smart Factory на Ubuntu сервер
# Запускать от имени root или с sudo

set -e  # Остановка при ошибке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Функции для вывода
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Проверка root прав
if [[ $EUID -ne 0 ]]; then
   print_error "Этот скрипт должен быть запущен от имени root или с sudo"
   exit 1
fi

print_info "Начинаем установку Smart Factory на Ubuntu сервер..."

# Переменные
SERVER_IP=$(hostname -I | awk '{print $1}')
DB_PASSWORD=$(openssl rand -base64 32)
SECRET_KEY=$(openssl rand -base64 64)
APP_USER="smartfactory"
APP_DIR="/home/$APP_USER/smart-factory"

print_info "IP адрес сервера: $SERVER_IP"
print_info "Пользователь приложения: $APP_USER"
print_info "Директория приложения: $APP_DIR"

# 1. Обновление системы
print_info "Обновление системы..."
apt update && apt upgrade -y

# 2. Установка необходимых пакетов
print_info "Установка необходимых пакетов..."
apt install -y python3 python3-pip python3-venv git nginx postgresql postgresql-contrib redis-server supervisor curl wget unzip ufw

# 3. Создание пользователя приложения
print_info "Создание пользователя приложения..."
if id "$APP_USER" &>/dev/null; then
    print_warning "Пользователь $APP_USER уже существует"
else
    adduser $APP_USER --disabled-password --gecos ""
    usermod -aG sudo $APP_USER
fi

# 4. Настройка PostgreSQL
print_info "Настройка PostgreSQL..."
sudo -u postgres psql -c "CREATE DATABASE smart_factory;" || print_warning "База данных уже существует"
sudo -u postgres psql -c "CREATE USER smart_factory_user WITH PASSWORD '$DB_PASSWORD';" || print_warning "Пользователь БД уже существует"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE smart_factory TO smart_factory_user;"
sudo -u postgres psql -c "ALTER USER smart_factory_user CREATEDB;"

# Оптимизация PostgreSQL
cat >> /etc/postgresql/*/main/postgresql.conf << EOF

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
EOF

systemctl restart postgresql
systemctl enable postgresql

# 5. Настройка Redis
print_info "Настройка Redis..."
sed -i 's/# maxmemory <bytes>/maxmemory 512mb/' /etc/redis/redis.conf
sed -i 's/# maxmemory-policy noeviction/maxmemory-policy allkeys-lru/' /etc/redis/redis.conf
sed -i 's/bind 127.0.0.1 ::1/bind 127.0.0.1/' /etc/redis/redis.conf

systemctl restart redis-server
systemctl enable redis-server

# 6. Клонирование проекта (если не существует)
if [ ! -d "$APP_DIR" ]; then
    print_info "Клонирование проекта..."
    sudo -u $APP_USER git clone https://github.com/byagge/sf.git $APP_DIR
else
    print_warning "Директория проекта уже существует"
fi

# 7. Настройка виртуального окружения
print_info "Настройка Python окружения..."
sudo -u $APP_USER bash -c "cd $APP_DIR && python3 -m venv venv"
sudo -u $APP_USER bash -c "cd $APP_DIR && source venv/bin/activate && pip install --upgrade pip"
sudo -u $APP_USER bash -c "cd $APP_DIR && source venv/bin/activate && pip install -r requirements_production.txt"
sudo -u $APP_USER bash -c "cd $APP_DIR && source venv/bin/activate && pip install psutil django-cacheops django-query-profiler"

# 8. Создание .env файла
print_info "Создание конфигурационного файла..."
sudo -u $APP_USER bash -c "cat > $APP_DIR/.env << EOF
DJANGO_SETTINGS_MODULE=core.settings_production
DJANGO_SECRET_KEY=$SECRET_KEY
DB_NAME=smart_factory
DB_USER=smart_factory_user
DB_PASSWORD=$DB_PASSWORD
DB_HOST=localhost
DB_PORT=5432
REDIS_URL=redis://127.0.0.1:6379
EMAIL_HOST=localhost
EMAIL_PORT=587
EMAIL_USE_TLS=False
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
EOF"

chmod 600 $APP_DIR/.env

# 9. Настройка Django
print_info "Настройка Django..."
sudo -u $APP_USER bash -c "cd $APP_DIR && source venv/bin/activate && python manage.py migrate"
sudo -u $APP_USER bash -c "cd $APP_DIR && source venv/bin/activate && python manage.py collectstatic --noinput"
sudo -u $APP_USER bash -c "mkdir -p $APP_DIR/logs && chmod 755 $APP_DIR/logs"

# 10. Создание systemd сервисов
print_info "Создание systemd сервисов..."

# Gunicorn сервис
cat > /etc/systemd/system/smartfactory.service << EOF
[Unit]
Description=Smart Factory Gunicorn daemon
After=network.target

[Service]
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin"
Environment="DJANGO_SETTINGS_MODULE=core.settings_production"
ExecStart=$APP_DIR/venv/bin/gunicorn --config gunicorn.conf.py core.wsgi:application
ExecReload=/bin/kill -s HUP \$MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

# Celery worker сервис
cat > /etc/systemd/system/smartfactory-celery.service << EOF
[Unit]
Description=Smart Factory Celery Worker
After=network.target

[Service]
Type=forking
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin"
Environment="DJANGO_SETTINGS_MODULE=core.settings_production"
ExecStart=$APP_DIR/venv/bin/celery multi start worker1 -A core -l info
ExecStop=$APP_DIR/venv/bin/celery multi stopwait worker1 -A core
ExecReload=$APP_DIR/venv/bin/celery multi restart worker1 -A core -l info

[Install]
WantedBy=multi-user.target
EOF

# Celery beat сервис
cat > /etc/systemd/system/smartfactory-celerybeat.service << EOF
[Unit]
Description=Smart Factory Celery Beat
After=network.target

[Service]
Type=simple
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin"
Environment="DJANGO_SETTINGS_MODULE=core.settings_production"
ExecStart=$APP_DIR/venv/bin/celery -A core beat -l info
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# 11. Настройка Nginx
print_info "Настройка Nginx..."
cat > /etc/nginx/sites-available/smartfactory << EOF
server {
    listen 80;
    server_name $SERVER_IP;

    client_max_body_size 10M;

    location /static/ {
        alias $APP_DIR/staticfiles/;
        expires 1y;
        add_header Cache-Control "public, immutable";
        access_log off;
    }

    location /media/ {
        alias $APP_DIR/media/;
        expires 1y;
        add_header Cache-Control "public";
        access_log off;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }

    location /health/ {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
EOF

# Активация сайта
ln -sf /etc/nginx/sites-available/smartfactory /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# 12. Настройка файрвола
print_info "Настройка файрвола..."
ufw --force enable
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp

# 13. Запуск сервисов
print_info "Запуск сервисов..."
systemctl daemon-reload
systemctl start smartfactory
systemctl enable smartfactory
systemctl start smartfactory-celery
systemctl enable smartfactory-celery
systemctl start smartfactory-celerybeat
systemctl enable smartfactory-celerybeat
systemctl restart nginx
systemctl enable nginx

# 14. Запуск оптимизации
print_info "Запуск оптимизации системы..."
sudo -u $APP_USER bash -c "cd $APP_DIR && source venv/bin/activate && python scripts/optimize_system.py"

# 15. Создание скриптов мониторинга
print_info "Создание скриптов мониторинга..."

# Скрипт мониторинга
cat > /home/$APP_USER/monitor.sh << 'EOF'
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
EOF

chmod +x /home/$APP_USER/monitor.sh

# Скрипт резервного копирования
cat > /home/$APP_USER/backup.sh << 'EOF'
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
EOF

chmod +x /home/$APP_USER/backup.sh

# 16. Настройка автоматических задач
print_info "Настройка автоматических задач..."
sudo -u $APP_USER bash -c "echo '0 9 * * * /home/$APP_USER/monitor.sh >> /home/$APP_USER/monitoring.log 2>&1' | crontab -"
sudo -u $APP_USER bash -c "echo '0 2 * * * /home/$APP_USER/backup.sh' | crontab -"

# 17. Финальная проверка
print_info "Проверка установки..."
sleep 5

# Проверка статуса сервисов
if systemctl is-active --quiet smartfactory; then
    print_info "✅ Gunicorn сервис запущен"
else
    print_error "❌ Gunicorn сервис не запущен"
fi

if systemctl is-active --quiet nginx; then
    print_info "✅ Nginx сервис запущен"
else
    print_error "❌ Nginx сервис не запущен"
fi

if systemctl is-active --quiet postgresql; then
    print_info "✅ PostgreSQL сервис запущен"
else
    print_error "❌ PostgreSQL сервис не запущен"
fi

if systemctl is-active --quiet redis-server; then
    print_info "✅ Redis сервис запущен"
else
    print_error "❌ Redis сервис не запущен"
fi

# 18. Вывод информации
print_info "=========================================="
print_info "🎉 УСТАНОВКА ЗАВЕРШЕНА УСПЕШНО!"
print_info "=========================================="
print_info ""
print_info "🌐 Доступ к приложению: http://$SERVER_IP"
print_info "🔧 Админ панель: http://$SERVER_IP/admin"
print_info "💚 Health check: http://$SERVER_IP/health"
print_info ""
print_info "📁 Директория приложения: $APP_DIR"
print_info "👤 Пользователь приложения: $APP_USER"
print_info "🗄️ База данных: smart_factory"
print_info "🔑 Пароль БД: $DB_PASSWORD"
print_info ""
print_info "📊 Полезные команды:"
print_info "  Проверка статуса: sudo systemctl status smartfactory"
print_info "  Просмотр логов: sudo journalctl -u smartfactory -f"
print_info "  Мониторинг: /home/$APP_USER/monitor.sh"
print_info "  Резервное копирование: /home/$APP_USER/backup.sh"
print_info ""
print_info "⚠️  НЕ ЗАБУДЬТЕ:"
print_info "  1. Создать суперпользователя: sudo -u $APP_USER bash -c 'cd $APP_DIR && source venv/bin/activate && python manage.py createsuperuser'"
print_info "  2. Изменить пароли в $APP_DIR/.env"
print_info "  3. Настроить SSL сертификат для production"
print_info "  4. Регулярно проверять логи и метрики"
print_info ""
print_info "==========================================" 