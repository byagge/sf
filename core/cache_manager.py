"""
Advanced cache management system for Smart Factory
Handles cache optimization, invalidation, and performance monitoring
"""

import hashlib
import json
import time
import logging
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from functools import wraps
from collections import defaultdict, deque
import threading

logger = logging.getLogger(__name__)


class CacheManager:
    """Advanced cache management system"""
    
    def __init__(self):
        self.cache_stats = defaultdict(lambda: {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
        })
        self.cache_keys = defaultdict(set)
        self.lock = threading.Lock()
    
    def get_cache_key(self, prefix, *args, **kwargs):
        """Generate a consistent cache key"""
        # Create a string representation of arguments
        key_parts = [prefix]
        
        if args:
            key_parts.extend([str(arg) for arg in args])
        
        if kwargs:
            # Sort kwargs for consistent keys
            sorted_kwargs = sorted(kwargs.items())
            key_parts.extend([f"{k}={v}" for k, v in sorted_kwargs])
        
        # Create hash for consistent key length
        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def get(self, key, default=None):
        """Get value from cache with statistics"""
        with self.lock:
            self.cache_stats[key]['hits'] += 1
        
        value = cache.get(key, default)
        
        if value is None:
            with self.lock:
                self.cache_stats[key]['misses'] += 1
        
        return value
    
    def set(self, key, value, timeout=None):
        """Set value in cache with statistics"""
        with self.lock:
            self.cache_stats[key]['sets'] += 1
            self.cache_keys[key].add(key)
        
        return cache.set(key, value, timeout)
    
    def delete(self, key):
        """Delete value from cache with statistics"""
        with self.lock:
            self.cache_stats[key]['deletes'] += 1
            self.cache_keys[key].discard(key)
        
        return cache.delete(key)
    
    def get_stats(self):
        """Get cache statistics"""
        with self.lock:
            return dict(self.cache_stats)
    
    def clear_stats(self):
        """Clear cache statistics"""
        with self.lock:
            self.cache_stats.clear()


class CacheDecorator:
    """Cache decorator with advanced features"""
    
    def __init__(self, timeout=300, key_prefix='', version=None):
        self.timeout = timeout
        self.key_prefix = key_prefix
        self.version = version
    
    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = self._generate_key(func, args, kwargs)
            
            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, self.timeout)
            
            return result
        
        return wrapper
    
    def _generate_key(self, func, args, kwargs):
        """Generate cache key for function"""
        key_parts = [
            self.key_prefix or func.__module__,
            func.__name__,
            str(hash(args)),
            str(hash(tuple(sorted(kwargs.items())))),
        ]
        
        if self.version:
            key_parts.append(str(self.version))
        
        return hashlib.md5("|".join(key_parts).encode()).hexdigest()


class CacheInvalidator:
    """Cache invalidation system"""
    
    def __init__(self):
        self.invalidation_patterns = defaultdict(set)
        self.lock = threading.Lock()
    
    def register_pattern(self, pattern, keys):
        """Register cache keys for a pattern"""
        with self.lock:
            self.invalidation_patterns[pattern].update(keys)
    
    def invalidate_pattern(self, pattern):
        """Invalidate all keys matching a pattern"""
        with self.lock:
            keys_to_delete = self.invalidation_patterns.get(pattern, set())
        
        deleted_count = 0
        for key in keys_to_delete:
            if cache.delete(key):
                deleted_count += 1
        
        logger.info(f"Invalidated {deleted_count} cache keys for pattern: {pattern}")
        return deleted_count
    
    def invalidate_model(self, model_name, instance_id=None):
        """Invalidate cache for a model"""
        pattern = f"{model_name}"
        if instance_id:
            pattern += f":{instance_id}"
        
        return self.invalidate_pattern(pattern)
    
    def invalidate_user(self, user_id):
        """Invalidate cache for a user"""
        return self.invalidate_pattern(f"user:{user_id}")
    
    def invalidate_workshop(self, workshop_id):
        """Invalidate cache for a workshop"""
        return self.invalidate_pattern(f"workshop:{workshop_id}")


class CacheOptimizer:
    """Cache optimization utilities"""
    
    @staticmethod
    def optimize_cache_settings():
        """Optimize cache settings for performance"""
        # Set cache compression
        if hasattr(cache, 'client'):
            if hasattr(cache.client, 'connection_pool'):
                # Optimize Redis connection pool
                pool = cache.client.connection_pool
                pool.max_connections = 50
                pool.retry_on_timeout = True
        
        logger.info("Cache settings optimized")
    
    @staticmethod
    def warm_cache():
        """Warm up cache with frequently accessed data"""
        from apps.users.models import User
        
        # Cache active users
        active_users = User.objects.filter(is_active_employee=True)
        for user in active_users:
            cache_key = f"user_stats_{user.id}"
            if not cache.get(cache_key):
                stats = user.get_statistics()
                cache.set(cache_key, stats, 300)
        
        # Cache user lists by role
        for role in User.Role.values:
            cache_key = f"role_users_{role}"
            if not cache.get(cache_key):
                users = list(User.objects.filter(role=role, is_active_employee=True))
                cache.set(cache_key, users, 600)
        
        logger.info("Cache warmed up with frequently accessed data")
    
    @staticmethod
    def cleanup_expired_cache():
        """Clean up expired cache entries"""
        # This is a simplified version. In production, you might need
        # a more sophisticated cache cleanup mechanism
        
        # Clear old session cache
        cache.delete_pattern('session:*')
        
        # Clear old user cache
        cache.delete_pattern('user_stats_*')
        
        logger.info("Expired cache entries cleaned up")


class CacheMonitor:
    """Cache performance monitoring"""
    
    def __init__(self):
        self.performance_metrics = deque(maxlen=1000)
        self.lock = threading.Lock()
    
    def record_operation(self, operation, key, duration, success):
        """Record cache operation performance"""
        with self.lock:
            self.performance_metrics.append({
                'operation': operation,
                'key': key,
                'duration': duration,
                'success': success,
                'timestamp': timezone.now(),
            })
    
    def get_performance_stats(self):
        """Get cache performance statistics"""
        with self.lock:
            metrics = list(self.performance_metrics)
        
        if not metrics:
            return {}
        
        # Calculate statistics
        operations = defaultdict(list)
        for metric in metrics:
            operations[metric['operation']].append(metric['duration'])
        
        stats = {}
        for operation, durations in operations.items():
            stats[operation] = {
                'count': len(durations),
                'average_time': sum(durations) / len(durations),
                'min_time': min(durations),
                'max_time': max(durations),
                'success_rate': sum(1 for m in metrics if m['operation'] == operation and m['success']) / len(durations),
            }
        
        return stats
    
    def get_slow_operations(self, threshold=0.1):
        """Get slow cache operations"""
        with self.lock:
            slow_ops = [
                metric for metric in self.performance_metrics
                if metric['duration'] > threshold
            ]
        
        return slow_ops


# Global instances
cache_manager = CacheManager()
cache_invalidator = CacheInvalidator()
cache_monitor = CacheMonitor()


def cached_function(timeout=300, key_prefix=''):
    """Decorator for caching function results"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = cache_manager.get_cache_key(
                key_prefix or func.__module__,
                func.__name__,
                *args,
                **kwargs
            )
            
            # Try to get from cache
            start_time = time.time()
            cached_result = cache_manager.get(cache_key)
            duration = time.time() - start_time
            
            cache_monitor.record_operation('get', cache_key, duration, cached_result is not None)
            
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            
            start_time = time.time()
            cache_manager.set(cache_key, result, timeout)
            duration = time.time() - start_time
            
            cache_monitor.record_operation('set', cache_key, duration, True)
            
            return result
        
        return wrapper
    return decorator


def invalidate_cache_pattern(pattern):
    """Invalidate cache by pattern"""
    return cache_invalidator.invalidate_pattern(pattern)


def invalidate_model_cache(model_name, instance_id=None):
    """Invalidate cache for a model"""
    return cache_invalidator.invalidate_model(model_name, instance_id)


def get_cache_performance_summary():
    """Get comprehensive cache performance summary"""
    return {
        'stats': cache_manager.get_stats(),
        'performance': cache_monitor.get_performance_stats(),
        'slow_operations': cache_monitor.get_slow_operations(),
    }


def optimize_cache():
    """Optimize cache for performance"""
    CacheOptimizer.optimize_cache_settings()
    CacheOptimizer.warm_cache()
    CacheOptimizer.cleanup_expired_cache()


# Cache patterns for common use cases
CACHE_PATTERNS = {
    'user_stats': 'user_stats_{user_id}',
    'user_tasks': 'user_tasks_{user_id}',
    'user_notifications': 'user_notifications_{user_id}',
    'workshop_users': 'workshop_users_{workshop_id}',
    'role_users': 'role_users_{role}',
    'employee_statistics': 'employee_statistics',
    'system_stats': 'system_stats',
    'performance_metrics': 'performance_metrics',
}


def cache_user_data(user_id, data_type, data, timeout=300):
    """Cache user-specific data"""
    pattern = CACHE_PATTERNS.get(data_type, data_type)
    cache_key = pattern.format(user_id=user_id)
    
    cache_manager.set(cache_key, data, timeout)
    
    # Register for invalidation
    cache_invalidator.register_pattern(f"user:{user_id}", {cache_key})


def get_cached_user_data(user_id, data_type, default=None):
    """Get cached user-specific data"""
    pattern = CACHE_PATTERNS.get(data_type, data_type)
    cache_key = pattern.format(user_id=user_id)
    
    return cache_manager.get(cache_key, default)


def invalidate_user_cache(user_id):
    """Invalidate all cache for a user"""
    return cache_invalidator.invalidate_user(user_id)


def cache_workshop_data(workshop_id, data_type, data, timeout=300):
    """Cache workshop-specific data"""
    pattern = CACHE_PATTERNS.get(data_type, data_type)
    cache_key = pattern.format(workshop_id=workshop_id)
    
    cache_manager.set(cache_key, data, timeout)
    
    # Register for invalidation
    cache_invalidator.register_pattern(f"workshop:{workshop_id}", {cache_key})


def get_cached_workshop_data(workshop_id, data_type, default=None):
    """Get cached workshop-specific data"""
    pattern = CACHE_PATTERNS.get(data_type, data_type)
    cache_key = pattern.format(workshop_id=workshop_id)
    
    return cache_manager.get(cache_key, default)


def invalidate_workshop_cache(workshop_id):
    """Invalidate all cache for a workshop"""
    return cache_invalidator.invalidate_workshop(workshop_id) 