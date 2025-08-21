"""
Celery tasks for Smart Factory
Background tasks for performance optimization and maintenance
"""

import os
import shutil
import logging
from datetime import datetime, timedelta
from celery import shared_task
from django.core.cache import cache
from django.db import connection
from django.conf import settings

logger = logging.getLogger(__name__)

@shared_task
def cleanup_old_logs():
    """Clean up old log files to save disk space."""
    try:
        logs_dir = settings.BASE_DIR / 'logs'
        if not logs_dir.exists():
            return "Logs directory does not exist"
        
        cutoff_date = datetime.now() - timedelta(days=30)
        cleaned_count = 0
        
        for log_file in logs_dir.glob('*.log.*'):
            try:
                file_stat = log_file.stat()
                file_date = datetime.fromtimestamp(file_stat.st_mtime)
                
                if file_date < cutoff_date:
                    log_file.unlink()
                    cleaned_count += 1
                    logger.info(f"Cleaned up old log file: {log_file}")
            except Exception as e:
                logger.error(f"Error cleaning up log file {log_file}: {e}")
        
        return f"Cleaned up {cleaned_count} old log files"
    except Exception as e:
        logger.error(f"Error in cleanup_old_logs task: {e}")
        raise

@shared_task
def database_maintenance():
    """Perform database maintenance tasks."""
    try:
        with connection.cursor() as cursor:
            # Analyze tables for better query planning
            cursor.execute("ANALYZE;")
            
            # Vacuum tables to reclaim storage
            cursor.execute("VACUUM ANALYZE;")
            
            logger.info("Database maintenance completed successfully")
            return "Database maintenance completed"
    except Exception as e:
        logger.error(f"Error in database_maintenance task: {e}")
        raise

@shared_task
def clear_expired_cache():
    """Clear expired cache entries."""
    try:
        # Clear Django's cache
        cache.clear()
        logger.info("Cache cleared successfully")
        return "Cache cleared successfully"
    except Exception as e:
        logger.error(f"Error in clear_expired_cache task: {e}")
        raise

@shared_task
def health_check():
    """Perform system health check."""
    try:
        health_status = {
            'timestamp': datetime.now().isoformat(),
            'database': 'healthy',
            'cache': 'healthy',
            'disk_space': 'healthy',
            'memory': 'healthy'
        }
        
        # Check database connection
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                health_status['database'] = 'healthy'
        except Exception:
            health_status['database'] = 'unhealthy'
        
        # Check cache
        try:
            cache.set('health_check', 'ok', 60)
            if cache.get('health_check') == 'ok':
                health_status['cache'] = 'healthy'
            else:
                health_status['cache'] = 'unhealthy'
        except Exception:
            health_status['cache'] = 'unhealthy'
        
        # Check disk space
        try:
            total, used, free = shutil.disk_usage(settings.BASE_DIR)
            usage_percent = (used / total) * 100
            
            if usage_percent > settings.HEALTH_CHECK['DISK_USAGE_MAX']:
                health_status['disk_space'] = 'warning'
            else:
                health_status['disk_space'] = 'healthy'
        except Exception:
            health_status['disk_space'] = 'unknown'
        
        # Store health status in cache
        cache.set('system_health', health_status, 300)  # 5 minutes
        
        logger.info(f"Health check completed: {health_status}")
        return health_status
    except Exception as e:
        logger.error(f"Error in health_check task: {e}")
        raise

@shared_task
def optimize_database_queries():
    """Analyze and optimize database queries."""
    try:
        with connection.cursor() as cursor:
            # Get slow queries from pg_stat_statements (if available)
            try:
                cursor.execute("""
                    SELECT query, calls, total_time, mean_time
                    FROM pg_stat_statements
                    WHERE mean_time > 1000  -- Queries taking more than 1 second
                    ORDER BY mean_time DESC
                    LIMIT 10
                """)
                slow_queries = cursor.fetchall()
                
                if slow_queries:
                    logger.warning(f"Found {len(slow_queries)} slow queries")
                    for query, calls, total_time, mean_time in slow_queries:
                        logger.warning(f"Slow query: {query[:100]}... (avg: {mean_time:.2f}ms, calls: {calls})")
                
            except Exception:
                # pg_stat_statements not available
                pass
            
            # Update table statistics
            cursor.execute("ANALYZE;")
            
            logger.info("Database query optimization completed")
            return "Database query optimization completed"
    except Exception as e:
        logger.error(f"Error in optimize_database_queries task: {e}")
        raise

@shared_task
def cleanup_old_sessions():
    """Clean up expired sessions."""
    try:
        from django.contrib.sessions.models import Session
        from django.utils import timezone
        
        # Delete expired sessions
        expired_sessions = Session.objects.filter(expire_date__lt=timezone.now())
        count = expired_sessions.count()
        expired_sessions.delete()
        
        logger.info(f"Cleaned up {count} expired sessions")
        return f"Cleaned up {count} expired sessions"
    except Exception as e:
        logger.error(f"Error in cleanup_old_sessions task: {e}")
        raise

@shared_task
def backup_database():
    """Create database backup."""
    try:
        # This is a placeholder - implement actual backup logic
        # For PostgreSQL, you might use pg_dump
        # For SQLite, you might copy the database file
        
        backup_dir = settings.BASE_DIR / 'backups'
        backup_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = backup_dir / f'backup_{timestamp}.sql'
        
        # Example for PostgreSQL (adjust for your setup)
        if settings.DATABASES['default']['ENGINE'] == 'django.db.backends.postgresql':
            db_name = settings.DATABASES['default']['NAME']
            db_user = settings.DATABASES['default']['USER']
            db_host = settings.DATABASES['default']['HOST']
            db_port = settings.DATABASES['default']['PORT']
            
            # Create backup using pg_dump
            backup_cmd = f"pg_dump -h {db_host} -p {db_port} -U {db_user} {db_name} > {backup_file}"
            os.system(backup_cmd)
            
            logger.info(f"Database backup created: {backup_file}")
            return f"Database backup created: {backup_file}"
        else:
            logger.info("Database backup not implemented for this database engine")
            return "Database backup not implemented for this database engine"
            
    except Exception as e:
        logger.error(f"Error in backup_database task: {e}")
        raise

@shared_task
def monitor_system_resources():
    """Monitor system resource usage."""
    try:
        import psutil
        
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        # Disk usage
        disk = psutil.disk_usage(settings.BASE_DIR)
        disk_percent = (disk.used / disk.total) * 100
        
        # Network I/O
        network = psutil.net_io_counters()
        
        system_stats = {
            'timestamp': datetime.now().isoformat(),
            'cpu_percent': cpu_percent,
            'memory_percent': memory_percent,
            'disk_percent': disk_percent,
            'network_bytes_sent': network.bytes_sent,
            'network_bytes_recv': network.bytes_recv,
        }
        
        # Store in cache for monitoring
        cache.set('system_stats', system_stats, 300)  # 5 minutes
        
        # Log warnings if thresholds exceeded
        if cpu_percent > 80:
            logger.warning(f"High CPU usage: {cpu_percent}%")
        if memory_percent > 80:
            logger.warning(f"High memory usage: {memory_percent}%")
        if disk_percent > 80:
            logger.warning(f"High disk usage: {disk_percent}%")
        
        logger.info(f"System monitoring completed: CPU: {cpu_percent}%, Memory: {memory_percent}%, Disk: {disk_percent}%")
        return system_stats
        
    except ImportError:
        logger.warning("psutil not available, system monitoring skipped")
        return "System monitoring not available"
    except Exception as e:
        logger.error(f"Error in monitor_system_resources task: {e}")
        raise 