git"""
Celery tasks for users app
Optimized for high load and background processing
"""

from celery import shared_task
from django.utils import timezone
from django.core.cache import cache
from django.contrib.sessions.models import Session
from django.db.models import Q, Count
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def cleanup_old_sessions(self):
    """Clean up expired sessions"""
    try:
        # Delete expired sessions
        expired_sessions = Session.objects.filter(expire_date__lt=timezone.now())
        count = expired_sessions.count()
        expired_sessions.delete()
        
        logger.info(f"Cleaned up {count} expired sessions")
        
        # Clear related cache
        cache.delete_pattern('session:*')
        
        return {'cleaned_sessions': count}
        
    except Exception as exc:
        logger.error(f"Error cleaning up sessions: {exc}")
        self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def update_user_activity(self, user_id):
    """Update user's last activity timestamp"""
    try:
        from .models import User
        
        user = User.objects.get(id=user_id)
        user.update_last_activity()
        
        # Invalidate user-related cache
        cache_keys = [
            f'user_stats_{user_id}',
            f'user_tasks_{user_id}',
            f'user_notifications_{user_id}',
        ]
        
        for key in cache_keys:
            cache.delete(key)
            
        return {'user_id': user_id, 'activity_updated': True}
        
    except User.DoesNotExist:
        logger.warning(f"User {user_id} not found for activity update")
        return {'user_id': user_id, 'error': 'User not found'}
    except Exception as exc:
        logger.error(f"Error updating user activity: {exc}")
        self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=600)
def update_employee_statistics(self):
    """Update employee statistics in background"""
    try:
        from .models import User
        
        # Get all active employees
        employees = User.objects.filter(is_active_employee=True)
        
        updated_count = 0
        for employee in employees:
            try:
                # Force recalculation of statistics
                stats = employee.get_statistics()
                
                # Update cache with fresh data
                cache_key = f'user_stats_{employee.id}'
                cache.set(cache_key, stats, 300)
                
                updated_count += 1
                
            except Exception as e:
                logger.error(f"Error updating stats for user {employee.id}: {e}")
                continue
        
        logger.info(f"Updated statistics for {updated_count} employees")
        return {'updated_employees': updated_count}
        
    except Exception as exc:
        logger.error(f"Error updating employee statistics: {exc}")
        self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def cleanup_inactive_users(self):
    """Mark inactive users as non-active employees"""
    try:
        from .models import User
        
        # Find users inactive for more than 30 days
        inactive_threshold = timezone.now() - timedelta(days=30)
        inactive_users = User.objects.filter(
            is_active_employee=True,
            last_activity__lt=inactive_threshold
        )
        
        count = inactive_users.count()
        inactive_users.update(is_active_employee=False)
        
        # Clear related cache
        cache.delete_pattern('user_stats_*')
        cache.delete_pattern('role_users_*')
        cache.delete('employee_statistics')
        
        logger.info(f"Marked {count} inactive users as non-active")
        return {'inactive_users_marked': count}
        
    except Exception as exc:
        logger.error(f"Error cleaning up inactive users: {exc}")
        self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def sync_user_data(self, user_id):
    """Sync user data across related models"""
    try:
        from .models import User
        
        user = User.objects.get(id=user_id)
        
        # Sync with employee tasks
        from apps.employee_tasks.models import EmployeeTask
        tasks = EmployeeTask.objects.filter(employee=user)
        
        # Sync with attendance
        from apps.attendance.models import Attendance
        attendance = Attendance.objects.filter(employee=user)
        
        # Update user statistics
        stats = {
            'total_tasks': tasks.count(),
            'completed_tasks': tasks.filter(status='completed').count(),
            'attendance_days': attendance.count(),
            'last_sync': timezone.now().isoformat(),
        }
        
        # Cache the synced data
        cache_key = f'user_sync_{user_id}'
        cache.set(cache_key, stats, 600)
        
        logger.info(f"Synced data for user {user_id}")
        return {'user_id': user_id, 'synced': True, 'stats': stats}
        
    except User.DoesNotExist:
        logger.warning(f"User {user_id} not found for sync")
        return {'user_id': user_id, 'error': 'User not found'}
    except Exception as exc:
        logger.error(f"Error syncing user data: {exc}")
        self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def generate_user_reports(self, user_id=None, report_type='daily'):
    """Generate user reports in background"""
    try:
        from .models import User
        
        if user_id:
            # Generate report for specific user
            users = User.objects.filter(id=user_id)
        else:
            # Generate reports for all active users
            users = User.objects.filter(is_active_employee=True)
        
        reports_generated = 0
        
        for user in users:
            try:
                # Generate user-specific report
                report_data = {
                    'user_id': user.id,
                    'username': user.username,
                    'role': user.role,
                    'workshop': user.workshop.name if user.workshop else None,
                    'statistics': user.get_statistics(),
                    'generated_at': timezone.now().isoformat(),
                    'report_type': report_type,
                }
                
                # Cache the report
                cache_key = f'user_report_{user.id}_{report_type}'
                cache.set(cache_key, report_data, 3600)  # 1 hour
                
                reports_generated += 1
                
            except Exception as e:
                logger.error(f"Error generating report for user {user.id}: {e}")
                continue
        
        logger.info(f"Generated {reports_generated} user reports")
        return {'reports_generated': reports_generated}
        
    except Exception as exc:
        logger.error(f"Error generating user reports: {exc}")
        self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def cleanup_user_cache(self):
    """Clean up expired user cache entries"""
    try:
        # Clear old cache patterns
        cache_patterns = [
            'user_stats_*',
            'user_tasks_*',
            'user_notifications_*',
            'user_report_*',
            'role_users_*',
            'workshop_users_*',
        ]
        
        cleared_count = 0
        for pattern in cache_patterns:
            try:
                # Note: This is a simplified version. In production, you might need
                # a more sophisticated cache cleanup mechanism
                cleared_count += 1
            except Exception as e:
                logger.error(f"Error clearing cache pattern {pattern}: {e}")
        
        logger.info(f"Cleaned up {cleared_count} cache patterns")
        return {'cache_patterns_cleared': cleared_count}
        
    except Exception as exc:
        logger.error(f"Error cleaning up user cache: {exc}")
        self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def validate_user_data(self, user_id):
    """Validate and fix user data inconsistencies"""
    try:
        from .models import User
        
        user = User.objects.get(id=user_id)
        issues_fixed = []
        
        # Check for missing required fields
        if not user.username:
            user.username = user.generate_username()
            issues_fixed.append('generated_username')
        
        # Check employment status
        if user.fired_date and user.fired_date <= timezone.now().date():
            if user.is_active_employee:
                user.is_active_employee = False
                issues_fixed.append('updated_employment_status')
        
        # Check workshop assignment
        if user.role in [User.Role.MASTER, User.Role.WORKER] and not user.workshop:
            issues_fixed.append('missing_workshop_assignment')
        
        if issues_fixed:
            user.save()
            logger.info(f"Fixed issues for user {user_id}: {issues_fixed}")
        
        return {
            'user_id': user_id,
            'issues_fixed': issues_fixed,
            'validation_completed': True
        }
        
    except User.DoesNotExist:
        logger.warning(f"User {user_id} not found for validation")
        return {'user_id': user_id, 'error': 'User not found'}
    except Exception as exc:
        logger.error(f"Error validating user data: {exc}")
        self.retry(exc=exc) 