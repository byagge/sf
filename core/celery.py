"""
Celery configuration for Smart Factory
Optimized for high load and stability
"""

import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings_production')

app = Celery('smart_factory')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

# Celery optimization settings
app.conf.update(
    # Broker settings
    broker_connection_retry_on_startup=True,
    broker_connection_max_retries=10,
    
    # Task settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Bishkek',
    enable_utc=True,
    
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    worker_disable_rate_limits=False,
    
    # Task routing
    task_routes={
        'apps.*.tasks.*': {'queue': 'default'},
        'apps.orders.tasks.*': {'queue': 'orders'},
        'apps.inventory.tasks.*': {'queue': 'inventory'},
        'apps.finance.tasks.*': {'queue': 'finance'},
        'apps.notifications.tasks.*': {'queue': 'notifications'},
    },
    
    # Queue settings
    task_default_queue='default',
    task_default_exchange='default',
    task_default_routing_key='default',
    
    # Result backend settings
    result_backend_transport_options={
        'master_name': "mymaster",
        'visibility_timeout': 3600,
    },
    
    # Beat settings for periodic tasks
    beat_schedule={
        'cleanup-old-sessions': {
            'task': 'apps.users.tasks.cleanup_old_sessions',
            'schedule': 3600.0,  # every hour
        },
        'update-inventory-status': {
            'task': 'apps.inventory.tasks.update_inventory_status',
            'schedule': 300.0,  # every 5 minutes
        },
        'generate-financial-reports': {
            'task': 'apps.finance.tasks.generate_daily_reports',
            'schedule': 86400.0,  # daily
        },
        'send-notifications': {
            'task': 'apps.notifications.tasks.send_pending_notifications',
            'schedule': 60.0,  # every minute
        },
    },
    
    # Task execution settings
    task_always_eager=False,
    task_eager_propagates=True,
    task_ignore_result=False,
    task_store_errors_even_if_ignored=True,
    
    # Security settings
    security_key=os.environ.get('CELERY_SECURITY_KEY'),
    security_certificate=os.environ.get('CELERY_SECURITY_CERTIFICATE'),
    security_cert_store=os.environ.get('CELERY_SECURITY_CERT_STORE'),
    
    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
    
    # Error handling
    task_reject_on_worker_lost=True,
    task_acks_late=True,
    
    # Performance
    worker_direct=False,
    task_compression='gzip',
    result_compression='gzip',
)

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

# Task error handling
@app.task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3})
def retry_task(self, *args, **kwargs):
    try:
        # Task logic here
        pass
    except Exception as exc:
        self.retry(exc=exc, countdown=60)  # Retry after 1 minute

# Health check task
@app.task
def health_check():
    """Simple health check task"""
    return {'status': 'healthy', 'timestamp': '2024-01-01T00:00:00Z'}

# Database cleanup task
@app.task
def cleanup_database():
    """Clean up old data from database"""
    from django.utils import timezone
    from datetime import timedelta
    
    # Clean up old sessions
    from django.contrib.sessions.models import Session
    Session.objects.filter(expire_date__lt=timezone.now()).delete()
    
    # Clean up old logs
    # Add your log cleanup logic here
    
    return {'cleaned_sessions': True}

# Performance monitoring task
@app.task
def monitor_performance():
    """Monitor system performance"""
    import psutil
    
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    return {
        'cpu_percent': cpu_percent,
        'memory_percent': memory.percent,
        'disk_percent': disk.percent,
        'timestamp': timezone.now().isoformat(),
    } 