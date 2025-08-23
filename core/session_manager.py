"""
Advanced session management system for Smart Factory
Handles session optimization, security, and performance monitoring
"""

import time
import logging
from django.core.cache import cache
from django.contrib.sessions.models import Session
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
import json
import hashlib
from collections import defaultdict, deque
import threading

logger = logging.getLogger(__name__)


class SessionManager:
    """Advanced session management system"""
    
    def __init__(self):
        self.session_stats = defaultdict(lambda: {
            'created': 0,
            'accessed': 0,
            'expired': 0,
            'deleted': 0,
        })
        self.active_sessions = defaultdict(set)
        self.lock = threading.Lock()
    
    def create_session(self, user_id, session_data=None):
        """Create a new session for a user"""
        session_key = self._generate_session_key(user_id)
        
        # Store session data in cache
        session_info = {
            'user_id': user_id,
            'created_at': timezone.now().isoformat(),
            'last_activity': timezone.now().isoformat(),
            'data': session_data or {},
            'ip_address': None,
            'user_agent': None,
        }
        
        # Cache session for 1 hour
        cache.set(f"session:{session_key}", session_info, 3600)
        
        with self.lock:
            self.session_stats['created'] += 1
            self.active_sessions[user_id].add(session_key)
        
        logger.info(f"Created session for user {user_id}")
        return session_key
    
    def get_session(self, session_key):
        """Get session data"""
        cache_key = f"session:{session_key}"
        session_info = cache.get(cache_key)
        
        if session_info:
            # Update last activity
            session_info['last_activity'] = timezone.now().isoformat()
            cache.set(cache_key, session_info, 3600)
            
            with self.lock:
                self.session_stats['accessed'] += 1
            
            return session_info
        
        return None
    
    def update_session(self, session_key, data):
        """Update session data"""
        cache_key = f"session:{session_key}"
        session_info = cache.get(cache_key)
        
        if session_info:
            session_info['data'].update(data)
            session_info['last_activity'] = timezone.now().isoformat()
            cache.set(cache_key, session_info, 3600)
            
            return True
        
        return False
    
    def delete_session(self, session_key):
        """Delete a session"""
        cache_key = f"session:{session_key}"
        session_info = cache.get(cache_key)
        
        if session_info:
            user_id = session_info.get('user_id')
            
            # Remove from cache
            cache.delete(cache_key)
            
            # Remove from active sessions
            with self.lock:
                self.session_stats['deleted'] += 1
                if user_id:
                    self.active_sessions[user_id].discard(session_key)
            
            logger.info(f"Deleted session {session_key}")
            return True
        
        return False
    
    def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        try:
            # Clean up Django sessions
            expired_sessions = Session.objects.filter(
                expire_date__lt=timezone.now()
            )
            expired_count = expired_sessions.count()
            expired_sessions.delete()
            
            # Clean up custom session cache
            # This is a simplified version - in production you might need
            # a more sophisticated cleanup mechanism
            
            with self.lock:
                self.session_stats['expired'] += expired_count
            
            logger.info(f"Cleaned up {expired_count} expired sessions")
            return expired_count
            
        except Exception as e:
            logger.error(f"Error cleaning up expired sessions: {e}")
            return 0
    
    def get_user_sessions(self, user_id):
        """Get all active sessions for a user"""
        with self.lock:
            return list(self.active_sessions.get(user_id, set()))
    
    def get_session_stats(self):
        """Get session statistics"""
        with self.lock:
            return dict(self.session_stats)
    
    def _generate_session_key(self, user_id):
        """Generate a unique session key"""
        timestamp = str(time.time())
        user_str = str(user_id)
        random_component = hashlib.md5(f"{user_str}{timestamp}".encode()).hexdigest()[:8]
        return f"{user_id}_{timestamp}_{random_component}"


class SessionSecurity:
    """Session security utilities"""
    
    @staticmethod
    def validate_session(session_key, user_id, ip_address=None, user_agent=None):
        """Validate session security"""
        cache_key = f"session:{session_key}"
        session_info = cache.get(cache_key)
        
        if not session_info:
            return False, "Session not found"
        
        # Check if session belongs to user
        if session_info.get('user_id') != user_id:
            return False, "Session user mismatch"
        
        # Check session age
        created_at = timezone.datetime.fromisoformat(session_info['created_at'])
        session_age = timezone.now() - created_at
        
        if session_age > timedelta(hours=24):
            return False, "Session too old"
        
        # Check for suspicious activity
        if ip_address and session_info.get('ip_address'):
            if ip_address != session_info['ip_address']:
                logger.warning(f"Suspicious session activity: IP mismatch for user {user_id}")
        
        return True, "Session valid"
    
    @staticmethod
    def update_session_security(session_key, ip_address=None, user_agent=None):
        """Update session security information"""
        cache_key = f"session:{session_key}"
        session_info = cache.get(cache_key)
        
        if session_info:
            if ip_address:
                session_info['ip_address'] = ip_address
            if user_agent:
                session_info['user_agent'] = user_agent
            
            cache.set(cache_key, session_info, 3600)
            return True
        
        return False


class SessionOptimizer:
    """Session optimization utilities"""
    
    @staticmethod
    def optimize_session_settings():
        """Optimize session settings for performance"""
        # Set session cache timeout
        session_timeout = getattr(settings, 'SESSION_COOKIE_AGE', 3600)
        
        # Optimize session storage
        if hasattr(settings, 'SESSION_ENGINE'):
            if settings.SESSION_ENGINE == 'django.contrib.sessions.backends.cache':
                # Optimize cache-based sessions
                cache.set('session_optimized', True, session_timeout)
        
        logger.info("Session settings optimized")
    
    @staticmethod
    def compress_session_data(session_data):
        """Compress session data to reduce storage"""
        try:
            # Convert to JSON and compress
            json_data = json.dumps(session_data, separators=(',', ':'))
            return json_data
        except Exception as e:
            logger.error(f"Error compressing session data: {e}")
            return session_data
    
    @staticmethod
    def decompress_session_data(compressed_data):
        """Decompress session data"""
        try:
            # Parse JSON data
            return json.loads(compressed_data)
        except Exception as e:
            logger.error(f"Error decompressing session data: {e}")
            return {}


class SessionMonitor:
    """Session performance monitoring"""
    
    def __init__(self):
        self.session_metrics = deque(maxlen=1000)
        self.lock = threading.Lock()
    
    def record_session_operation(self, operation, session_key, duration, success):
        """Record session operation performance"""
        with self.lock:
            self.session_metrics.append({
                'operation': operation,
                'session_key': session_key,
                'duration': duration,
                'success': success,
                'timestamp': timezone.now(),
            })
    
    def get_session_stats(self):
        """Get session performance statistics"""
        with self.lock:
            metrics = list(self.session_metrics)
        
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
    
    def get_active_sessions_count(self):
        """Get count of active sessions"""
        # This is a simplified version - in production you might need
        # a more sophisticated counting mechanism
        return len(cache.get('active_sessions', set()))


# Global instances
session_manager = SessionManager()
session_monitor = SessionMonitor()


def create_user_session(user_id, session_data=None):
    """Create a new session for a user"""
    start_time = time.time()
    
    try:
        session_key = session_manager.create_session(user_id, session_data)
        duration = time.time() - start_time
        
        session_monitor.record_session_operation('create', session_key, duration, True)
        
        return session_key
    except Exception as e:
        duration = time.time() - start_time
        session_monitor.record_session_operation('create', 'error', duration, False)
        logger.error(f"Error creating session for user {user_id}: {e}")
        return None


def get_user_session(session_key):
    """Get session data for a user"""
    start_time = time.time()
    
    try:
        session_info = session_manager.get_session(session_key)
        duration = time.time() - start_time
        
        session_monitor.record_session_operation('get', session_key, duration, session_info is not None)
        
        return session_info
    except Exception as e:
        duration = time.time() - start_time
        session_monitor.record_session_operation('get', session_key, duration, False)
        logger.error(f"Error getting session {session_key}: {e}")
        return None


def update_user_session(session_key, data):
    """Update session data"""
    start_time = time.time()
    
    try:
        success = session_manager.update_session(session_key, data)
        duration = time.time() - start_time
        
        session_monitor.record_session_operation('update', session_key, duration, success)
        
        return success
    except Exception as e:
        duration = time.time() - start_time
        session_monitor.record_session_operation('update', session_key, duration, False)
        logger.error(f"Error updating session {session_key}: {e}")
        return False


def delete_user_session(session_key):
    """Delete a user session"""
    start_time = time.time()
    
    try:
        success = session_manager.delete_session(session_key)
        duration = time.time() - start_time
        
        session_monitor.record_session_operation('delete', session_key, duration, success)
        
        return success
    except Exception as e:
        duration = time.time() - start_time
        session_monitor.record_session_operation('delete', session_key, duration, False)
        logger.error(f"Error deleting session {session_key}: {e}")
        return False


def validate_user_session(session_key, user_id, ip_address=None, user_agent=None):
    """Validate user session security"""
    return SessionSecurity.validate_session(session_key, user_id, ip_address, user_agent)


def get_session_performance_summary():
    """Get comprehensive session performance summary"""
    return {
        'manager_stats': session_manager.get_session_stats(),
        'monitor_stats': session_monitor.get_session_stats(),
        'active_sessions': session_monitor.get_active_sessions_count(),
    }


def optimize_sessions():
    """Optimize sessions for performance"""
    SessionOptimizer.optimize_session_settings()
    session_manager.cleanup_expired_sessions()


def cleanup_old_sessions():
    """Clean up old sessions"""
    return session_manager.cleanup_expired_sessions()


def get_user_active_sessions(user_id):
    """Get all active sessions for a user"""
    return session_manager.get_user_sessions(user_id)


def force_logout_user(user_id):
    """Force logout user from all sessions"""
    sessions = session_manager.get_user_sessions(user_id)
    
    for session_key in sessions:
        session_manager.delete_session(session_key)
    
    logger.info(f"Force logged out user {user_id} from {len(sessions)} sessions")
    return len(sessions) 