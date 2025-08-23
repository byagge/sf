"""
Database optimization utilities for Smart Factory
Handles connection pooling, query optimization, and performance monitoring
"""

import logging
from django.db import connection, connections
from django.conf import settings
from django.core.cache import cache
from contextlib import contextmanager
import time

logger = logging.getLogger(__name__)


class DatabaseOptimizer:
    """Database optimization utilities"""
    
    @staticmethod
    def optimize_connections():
        """Optimize database connections"""
        for alias in connections.databases:
            connection = connections[alias]
            
            # Set connection parameters
            if hasattr(connection, 'connection'):
                conn = connection.connection
                if hasattr(conn, 'set_timeout'):
                    conn.set_timeout(30)  # 30 seconds timeout
                
                # Set connection pool settings for PostgreSQL
                if connection.vendor == 'postgresql':
                    conn.set_session(autocommit=True)
    
    @staticmethod
    def get_connection_stats():
        """Get database connection statistics"""
        stats = {}
        
        for alias in connections.databases:
            connection = connections[alias]
            stats[alias] = {
                'vendor': connection.vendor,
                'database': connection.settings_dict.get('NAME'),
                'host': connection.settings_dict.get('HOST'),
                'port': connection.settings_dict.get('PORT'),
            }
            
            # Get connection info if available
            if hasattr(connection, 'connection') and connection.connection:
                try:
                    if connection.vendor == 'postgresql':
                        with connection.cursor() as cursor:
                            cursor.execute("""
                                SELECT 
                                    count(*) as active_connections,
                                    max_conn as max_connections
                                FROM pg_stat_activity, pg_settings 
                                WHERE name = 'max_connections'
                            """)
                            result = cursor.fetchone()
                            if result:
                                stats[alias]['active_connections'] = result[0]
                                stats[alias]['max_connections'] = result[1]
                except Exception as e:
                    logger.warning(f"Could not get connection stats for {alias}: {e}")
        
        return stats
    
    @staticmethod
    def monitor_slow_queries():
        """Monitor and log slow database queries"""
        if not settings.DEBUG:
            return
        
        queries = getattr(connection, 'queries', [])
        slow_queries = []
        
        for query in queries:
            if float(query['time']) > 0.1:  # Queries taking more than 100ms
                slow_queries.append({
                    'sql': query['sql'],
                    'time': query['time'],
                    'stack': query.get('stack', ''),
                })
        
        if slow_queries:
            logger.warning(f"Found {len(slow_queries)} slow queries")
            for query in slow_queries:
                logger.warning(f"Slow query ({query['time']}s): {query['sql'][:200]}...")


@contextmanager
def optimized_query_context():
    """Context manager for optimized database queries"""
    start_time = time.time()
    
    try:
        # Optimize connections before query
        DatabaseOptimizer.optimize_connections()
        
        yield
        
    finally:
        # Monitor performance after query
        duration = time.time() - start_time
        if duration > 0.5:  # Log queries taking more than 500ms
            logger.warning(f"Slow query context took {duration:.3f}s")
        
        # Monitor slow queries
        DatabaseOptimizer.monitor_slow_queries()


class QueryOptimizer:
    """Query optimization utilities"""
    
    @staticmethod
    def optimize_queryset(queryset, select_related=None, prefetch_related=None):
        """Optimize queryset with select_related and prefetch_related"""
        if select_related:
            queryset = queryset.select_related(*select_related)
        
        if prefetch_related:
            queryset = queryset.prefetch_related(*prefetch_related)
        
        return queryset
    
    @staticmethod
    def bulk_operations(model, objects, operation='create', batch_size=1000):
        """Perform bulk operations with batching"""
        if not objects:
            return []
        
        if operation == 'create':
            return model.objects.bulk_create(objects, batch_size=batch_size)
        elif operation == 'update':
            return model.objects.bulk_update(objects, batch_size=batch_size)
        elif operation == 'delete':
            return model.objects.filter(id__in=[obj.id for obj in objects]).delete()
        
        return []
    
    @staticmethod
    def cache_queryset(queryset, cache_key, timeout=300):
        """Cache queryset results"""
        cached_result = cache.get(cache_key)
        
        if cached_result is None:
            cached_result = list(queryset)
            cache.set(cache_key, cached_result, timeout)
        
        return cached_result


class DatabaseMaintenance:
    """Database maintenance utilities"""
    
    @staticmethod
    def vacuum_database():
        """Perform database vacuum (PostgreSQL only)"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("VACUUM ANALYZE;")
                logger.info("Database vacuum completed")
        except Exception as e:
            logger.error(f"Error during database vacuum: {e}")
    
    @staticmethod
    def reindex_database():
        """Reindex database tables (PostgreSQL only)"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("REINDEX DATABASE %s;" % connection.settings_dict['NAME'])
                logger.info("Database reindex completed")
        except Exception as e:
            logger.error(f"Error during database reindex: {e}")
    
    @staticmethod
    def update_statistics():
        """Update database statistics (PostgreSQL only)"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("ANALYZE;")
                logger.info("Database statistics updated")
        except Exception as e:
            logger.error(f"Error updating database statistics: {e}")
    
    @staticmethod
    def cleanup_old_data():
        """Clean up old data from database"""
        from django.utils import timezone
        from datetime import timedelta
        
        # Clean up old sessions
        from django.contrib.sessions.models import Session
        old_sessions = Session.objects.filter(
            expire_date__lt=timezone.now() - timedelta(days=7)
        )
        deleted_sessions = old_sessions.count()
        old_sessions.delete()
        
        # Clean up old logs
        # Add your log cleanup logic here
        
        logger.info(f"Cleaned up {deleted_sessions} old sessions")
        return {'deleted_sessions': deleted_sessions}


class ConnectionPool:
    """Database connection pool management"""
    
    @staticmethod
    def get_connection_pool_stats():
        """Get connection pool statistics"""
        stats = {}
        
        for alias in connections.databases:
            connection = connections[alias]
            stats[alias] = {
                'vendor': connection.vendor,
                'database': connection.settings_dict.get('NAME'),
            }
            
            # Get pool stats if available
            if hasattr(connection, 'connection') and connection.connection:
                try:
                    if connection.vendor == 'postgresql':
                        with connection.cursor() as cursor:
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
                                stats[alias].update({
                                    'total_connections': result[0],
                                    'active_connections': result[1],
                                    'idle_connections': result[2],
                                })
                except Exception as e:
                    logger.warning(f"Could not get pool stats for {alias}: {e}")
        
        return stats
    
    @staticmethod
    def close_idle_connections():
        """Close idle database connections"""
        for alias in connections.databases:
            connection = connections[alias]
            
            if hasattr(connection, 'close_if_unusable_or_obsolete'):
                connection.close_if_unusable_or_obsolete()
        
        logger.info("Closed idle database connections")


# Utility functions
def get_database_performance_metrics():
    """Get database performance metrics"""
    metrics = {
        'connection_stats': DatabaseOptimizer.get_connection_stats(),
        'pool_stats': ConnectionPool.get_connection_pool_stats(),
        'slow_queries_count': len([q for q in getattr(connection, 'queries', []) 
                                 if float(q['time']) > 0.1]),
    }
    
    return metrics


def optimize_database_settings():
    """Apply database optimization settings"""
    # Optimize connections
    DatabaseOptimizer.optimize_connections()
    
    # Set connection pool settings
    for alias in connections.databases:
        connection = connections[alias]
        
        # Set connection parameters
        if hasattr(connection, 'settings_dict'):
            settings_dict = connection.settings_dict
            
            # Set connection timeout
            if 'OPTIONS' not in settings_dict:
                settings_dict['OPTIONS'] = {}
            
            settings_dict['OPTIONS'].update({
                'connect_timeout': 30,
                'read_timeout': 30,
                'write_timeout': 30,
            })
    
    logger.info("Database optimization settings applied") 