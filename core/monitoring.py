"""
Performance monitoring system for Smart Factory
Tracks system performance, database queries, and application metrics
"""

import time
import psutil
import logging
from django.core.cache import cache
from django.conf import settings
from django.db import connection
from django.utils import timezone
from datetime import datetime, timedelta
import json
import threading
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """Main performance monitoring class"""
    
    def __init__(self):
        self.metrics = defaultdict(deque)
        self.max_metrics = 1000  # Keep last 1000 metrics
        self.lock = threading.Lock()
        
    def record_metric(self, metric_type, value, tags=None):
        """Record a performance metric"""
        with self.lock:
            timestamp = timezone.now()
            metric_data = {
                'timestamp': timestamp,
                'value': value,
                'tags': tags or {}
            }
            
            self.metrics[metric_type].append(metric_data)
            
            # Keep only the last max_metrics
            if len(self.metrics[metric_type]) > self.max_metrics:
                self.metrics[metric_type].popleft()
    
    def get_metrics(self, metric_type, minutes=60):
        """Get metrics for the last N minutes"""
        if metric_type not in self.metrics:
            return []
        
        cutoff_time = timezone.now() - timedelta(minutes=minutes)
        
        with self.lock:
            return [
                metric for metric in self.metrics[metric_type]
                if metric['timestamp'] >= cutoff_time
            ]
    
    def get_average(self, metric_type, minutes=60):
        """Get average value for a metric type"""
        metrics = self.get_metrics(metric_type, minutes)
        if not metrics:
            return 0
        
        values = [m['value'] for m in metrics]
        return sum(values) / len(values)
    
    def get_percentile(self, metric_type, percentile=95, minutes=60):
        """Get percentile value for a metric type"""
        metrics = self.get_metrics(metric_type, minutes)
        if not metrics:
            return 0
        
        values = sorted([m['value'] for m in metrics])
        index = int(len(values) * percentile / 100)
        return values[index] if index < len(values) else values[-1]


class SystemMonitor:
    """System resource monitoring"""
    
    @staticmethod
    def get_system_stats():
        """Get current system statistics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available': memory.available,
                'memory_total': memory.total,
                'disk_percent': disk.percent,
                'disk_free': disk.free,
                'disk_total': disk.total,
                'timestamp': timezone.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Error getting system stats: {e}")
            return {}
    
    @staticmethod
    def get_process_stats():
        """Get current process statistics"""
        try:
            process = psutil.Process()
            
            return {
                'cpu_percent': process.cpu_percent(),
                'memory_percent': process.memory_percent(),
                'memory_rss': process.memory_info().rss,
                'memory_vms': process.memory_info().vms,
                'num_threads': process.num_threads(),
                'num_fds': process.num_fds() if hasattr(process, 'num_fds') else 0,
                'timestamp': timezone.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Error getting process stats: {e}")
            return {}


class DatabaseMonitor:
    """Database performance monitoring"""
    
    @staticmethod
    def get_query_stats():
        """Get database query statistics"""
        if not settings.DEBUG:
            return {}
        
        queries = getattr(connection, 'queries', [])
        if not queries:
            return {}
        
        total_time = sum(float(q['time']) for q in queries)
        slow_queries = [q for q in queries if float(q['time']) > 0.1]
        
        return {
            'total_queries': len(queries),
            'total_time': total_time,
            'average_time': total_time / len(queries) if queries else 0,
            'slow_queries': len(slow_queries),
            'slowest_query': max(queries, key=lambda x: float(x['time'])) if queries else None,
        }
    
    @staticmethod
    def get_connection_stats():
        """Get database connection statistics"""
        try:
            with connection.cursor() as cursor:
                if connection.vendor == 'postgresql':
                    cursor.execute("""
                        SELECT 
                            count(*) as total_connections,
                            count(*) FILTER (WHERE state = 'active') as active_connections,
                            count(*) FILTER (WHERE state = 'idle') as idle_connections
                        FROM pg_stat_activity 
                        WHERE datname = %s
                    """, [connection.settings_dict['NAME']])
                    
                    result = cursor.fetchone()
                    if result:
                        return {
                            'total_connections': result[0],
                            'active_connections': result[1],
                            'idle_connections': result[2],
                        }
        except Exception as e:
            logger.error(f"Error getting connection stats: {e}")
        
        return {}


class CacheMonitor:
    """Cache performance monitoring"""
    
    @staticmethod
    def get_cache_stats():
        """Get cache statistics"""
        try:
            # Test cache performance
            test_key = 'cache_performance_test'
            start_time = time.time()
            
            cache.set(test_key, 'test_value', 60)
            read_start = time.time()
            cache.get(test_key)
            read_end = time.time()
            
            cache.delete(test_key)
            
            return {
                'write_time': read_start - start_time,
                'read_time': read_end - read_start,
                'total_time': read_end - start_time,
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {}


class RequestMonitor:
    """Request performance monitoring"""
    
    def __init__(self):
        self.request_times = deque(maxlen=1000)
        self.error_counts = defaultdict(int)
        self.endpoint_stats = defaultdict(lambda: {
            'count': 0,
            'total_time': 0,
            'errors': 0,
        })
    
    def record_request(self, path, method, duration, status_code):
        """Record request performance"""
        self.request_times.append(duration)
        
        # Record endpoint statistics
        endpoint = f"{method} {path}"
        self.endpoint_stats[endpoint]['count'] += 1
        self.endpoint_stats[endpoint]['total_time'] += duration
        
        if status_code >= 400:
            self.endpoint_stats[endpoint]['errors'] += 1
            self.error_counts[status_code] += 1
    
    def get_request_stats(self):
        """Get request statistics"""
        if not self.request_times:
            return {}
        
        times = list(self.request_times)
        return {
            'total_requests': len(times),
            'average_time': sum(times) / len(times),
            'min_time': min(times),
            'max_time': max(times),
            'p95_time': sorted(times)[int(len(times) * 0.95)],
            'p99_time': sorted(times)[int(len(times) * 0.99)],
            'error_counts': dict(self.error_counts),
        }
    
    def get_endpoint_stats(self):
        """Get endpoint-specific statistics"""
        stats = {}
        for endpoint, data in self.endpoint_stats.items():
            if data['count'] > 0:
                stats[endpoint] = {
                    'count': data['count'],
                    'average_time': data['total_time'] / data['count'],
                    'error_rate': data['errors'] / data['count'],
                }
        
        return stats


class HealthChecker:
    """System health checking"""
    
    @staticmethod
    def check_database_health():
        """Check database health"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                return {'status': 'healthy', 'response_time': 0}
        except Exception as e:
            return {'status': 'unhealthy', 'error': str(e)}
    
    @staticmethod
    def check_cache_health():
        """Check cache health"""
        try:
            test_key = 'health_check'
            cache.set(test_key, 'test', 10)
            result = cache.get(test_key)
            cache.delete(test_key)
            
            if result == 'test':
                return {'status': 'healthy'}
            else:
                return {'status': 'unhealthy', 'error': 'Cache read/write failed'}
        except Exception as e:
            return {'status': 'unhealthy', 'error': str(e)}
    
    @staticmethod
    def check_system_health():
        """Check overall system health"""
        try:
            # Check system resources
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            health_status = 'healthy'
            issues = []
            
            if memory.percent > 90:
                health_status = 'warning'
                issues.append('High memory usage')
            
            if disk.percent > 90:
                health_status = 'warning'
                issues.append('High disk usage')
            
            return {
                'status': health_status,
                'issues': issues,
                'memory_percent': memory.percent,
                'disk_percent': disk.percent,
            }
        except Exception as e:
            return {'status': 'unhealthy', 'error': str(e)}
    
    @staticmethod
    def get_full_health_report():
        """Get comprehensive health report"""
        return {
            'database': HealthChecker.check_database_health(),
            'cache': HealthChecker.check_cache_health(),
            'system': HealthChecker.check_system_health(),
            'timestamp': timezone.now().isoformat(),
        }


class AlertManager:
    """Performance alert management"""
    
    def __init__(self):
        self.alerts = deque(maxlen=100)
        self.thresholds = {
            'cpu_percent': 80,
            'memory_percent': 85,
            'disk_percent': 90,
            'response_time_p95': 2.0,  # 2 seconds
            'error_rate': 0.05,  # 5%
            'slow_queries': 10,
        }
    
    def check_alerts(self, metrics):
        """Check for performance alerts"""
        alerts = []
        
        # System alerts
        if metrics.get('cpu_percent', 0) > self.thresholds['cpu_percent']:
            alerts.append({
                'type': 'high_cpu',
                'message': f"High CPU usage: {metrics['cpu_percent']}%",
                'severity': 'warning',
                'timestamp': timezone.now(),
            })
        
        if metrics.get('memory_percent', 0) > self.thresholds['memory_percent']:
            alerts.append({
                'type': 'high_memory',
                'message': f"High memory usage: {metrics['memory_percent']}%",
                'severity': 'warning',
                'timestamp': timezone.now(),
            })
        
        # Performance alerts
        if metrics.get('response_time_p95', 0) > self.thresholds['response_time_p95']:
            alerts.append({
                'type': 'slow_response',
                'message': f"Slow response time (P95): {metrics['response_time_p95']}s",
                'severity': 'warning',
                'timestamp': timezone.now(),
            })
        
        # Database alerts
        if metrics.get('slow_queries', 0) > self.thresholds['slow_queries']:
            alerts.append({
                'type': 'slow_queries',
                'message': f"Too many slow queries: {metrics['slow_queries']}",
                'severity': 'warning',
                'timestamp': timezone.now(),
            })
        
        # Store alerts
        for alert in alerts:
            self.alerts.append(alert)
            logger.warning(f"Performance alert: {alert['message']}")
        
        return alerts
    
    def get_recent_alerts(self, hours=24):
        """Get recent alerts"""
        cutoff_time = timezone.now() - timedelta(hours=hours)
        return [
            alert for alert in self.alerts
            if alert['timestamp'] >= cutoff_time
        ]


# Global instances
performance_monitor = PerformanceMonitor()
request_monitor = RequestMonitor()
alert_manager = AlertManager()


def record_request_metrics(path, method, duration, status_code):
    """Record request metrics"""
    request_monitor.record_request(path, method, duration, status_code)
    
    # Record performance metrics
    performance_monitor.record_metric('request_duration', duration)
    performance_monitor.record_metric('request_count', 1)
    
    if status_code >= 400:
        performance_monitor.record_metric('error_count', 1)


def get_performance_summary():
    """Get comprehensive performance summary"""
    system_stats = SystemMonitor.get_system_stats()
    process_stats = SystemMonitor.get_process_stats()
    db_stats = DatabaseMonitor.get_query_stats()
    cache_stats = CacheMonitor.get_cache_stats()
    request_stats = request_monitor.get_request_stats()
    health_report = HealthChecker.get_full_health_report()
    
    # Combine all metrics
    summary = {
        'system': system_stats,
        'process': process_stats,
        'database': db_stats,
        'cache': cache_stats,
        'requests': request_stats,
        'health': health_report,
        'timestamp': timezone.now().isoformat(),
    }
    
    # Check for alerts
    combined_metrics = {
        'cpu_percent': system_stats.get('cpu_percent', 0),
        'memory_percent': system_stats.get('memory_percent', 0),
        'disk_percent': system_stats.get('disk_percent', 0),
        'response_time_p95': request_stats.get('p95_time', 0),
        'slow_queries': db_stats.get('slow_queries', 0),
    }
    
    alerts = alert_manager.check_alerts(combined_metrics)
    summary['alerts'] = alerts
    
    return summary


def log_performance_metrics():
    """Log performance metrics periodically"""
    summary = get_performance_summary()
    
    # Log key metrics
    logger.info(f"Performance summary: CPU={summary['system'].get('cpu_percent', 0)}%, "
                f"Memory={summary['system'].get('memory_percent', 0)}%, "
                f"Requests={summary['requests'].get('total_requests', 0)}, "
                f"Avg Response={summary['requests'].get('average_time', 0):.3f}s")
    
    # Log alerts
    if summary['alerts']:
        for alert in summary['alerts']:
            logger.warning(f"Performance alert: {alert['message']}")
    
    return summary 