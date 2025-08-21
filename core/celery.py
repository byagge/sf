"""
Celery configuration for Smart Factory
Handles background tasks and performance optimization
"""

import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings_production')

# Create celery app
app = Celery('smart_factory')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

# Celery configuration
app.conf.update(
    # Broker settings
    broker_url=os.environ.get('CELERY_BROKER_URL', 'redis://127.0.0.1:6379/0'),
    result_backend=os.environ.get('CELERY_RESULT_BACKEND', 'redis://127.0.0.1:6379/0'),
    
    # Task settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone=settings.TIME_ZONE,
    enable_utc=True,
    
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    worker_max_memory_per_child=200000,  # 200MB
    
    # Task routing
    task_routes={
        'apps.orders.tasks.*': {'queue': 'orders'},
        'apps.finance.tasks.*': {'queue': 'finance'},
        'apps.defects.tasks.*': {'queue': 'defects'},
        'apps.employee_tasks.tasks.*': {'queue': 'tasks'},
        'apps.inventory.tasks.*': {'queue': 'inventory'},
    },
    
    # Queue configuration
    task_default_queue='default',
    task_queues={
        'default': {
            'exchange': 'default',
            'routing_key': 'default',
        },
        'orders': {
            'exchange': 'orders',
            'routing_key': 'orders',
        },
        'finance': {
            'exchange': 'finance',
            'routing_key': 'finance',
        },
        'defects': {
            'exchange': 'defects',
            'routing_key': 'defects',
        },
        'tasks': {
            'exchange': 'tasks',
            'routing_key': 'tasks',
        },
        'inventory': {
            'exchange': 'inventory',
            'routing_key': 'inventory',
        },
    },
    
    # Task execution settings
    task_always_eager=False,
    task_eager_propagates=True,
    task_ignore_result=False,
    task_store_errors_even_if_ignored=True,
    
    # Result backend settings
    result_expires=3600,  # 1 hour
    result_persistent=True,
    
    # Beat settings (for periodic tasks)
    beat_schedule={
        'cleanup-old-sessions': {
            'task': 'django.contrib.sessions.tasks.cleanup_sessions',
            'schedule': 86400.0,  # Daily
        },
        'update-order-statistics': {
            'task': 'apps.orders.tasks.update_order_statistics',
            'schedule': 3600.0,  # Hourly
        },
        'cleanup-old-logs': {
            'task': 'core.tasks.cleanup_old_logs',
            'schedule': 86400.0,  # Daily
        },
        'database-maintenance': {
            'task': 'core.tasks.database_maintenance',
            'schedule': 604800.0,  # Weekly
        },
    },
    
    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
    
    # Error handling
    task_reject_on_worker_lost=True,
    task_acks_late=True,
    
    # Performance optimization
    worker_disable_rate_limits=False,
    worker_cancel_long_running_tasks_on_connection_loss=True,
)

@app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery setup."""
    print(f'Request: {self.request!r}')

# Import tasks after app is configured
from . import tasks 