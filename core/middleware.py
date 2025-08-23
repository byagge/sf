"""
Optimized middleware for Smart Factory
Handles caching, security, and performance optimization
"""

import time
import hashlib
from django.utils.cache import get_cache_key, learn_cache_key
from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponse
from django.conf import settings
from django.core.cache import cache
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone
from django.shortcuts import redirect
from django.urls import reverse
import logging

logger = logging.getLogger(__name__)


class RoleBasedRedirectMiddleware(MiddlewareMixin):
    """Middleware for role-based redirects"""
    
    def process_request(self, request):
        if not request.user.is_authenticated:
            return None
            
        # Skip for API requests
        if request.path.startswith('/api/'):
            return None
            
        # Skip for admin
        if request.path.startswith('/admin/'):
            return None
            
        # Skip for static files
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            return None
            
        # Role-based redirects
        if request.path == '/':
            if hasattr(request.user, 'role'):
                if request.user.role == 'director':
                    return redirect('director:dashboard')
                elif request.user.role == 'executive':
                    return redirect('executive:dashboard')
                elif request.user.role == 'manager':
                    return redirect('manager:dashboard')
                elif request.user.role == 'employee':
                    return redirect('employee:dashboard')
                    
        return None


class CacheMiddleware(MiddlewareMixin):
    """Advanced caching middleware with user-specific cache keys"""
    
    def process_request(self, request):
        # Skip caching for authenticated users on dynamic pages
        if request.user.is_authenticated and not request.path.startswith('/static/'):
            return None
            
        # Skip for POST requests
        if request.method != 'GET':
            return None
            
        # Skip for admin and API
        if request.path.startswith('/admin/') or request.path.startswith('/api/'):
            return None
            
        # Generate cache key
        cache_key = self._get_cache_key(request)
        if cache_key:
            response = cache.get(cache_key)
            if response:
                return response
                
        return None
        
    def process_response(self, request, response):
        # Skip caching for non-GET requests
        if request.method != 'GET':
            return response
            
        # Skip for admin and API
        if request.path.startswith('/admin/') or request.path.startswith('/api/'):
            return response
            
        # Skip for authenticated users on dynamic pages
        if request.user.is_authenticated:
            return response
            
        # Only cache successful responses
        if response.status_code == 200:
            cache_key = self._get_cache_key(request)
            if cache_key:
                # Cache for 5 minutes for anonymous users
                cache.set(cache_key, response, 300)
                
        return response
        
    def _get_cache_key(self, request):
        """Generate cache key based on request"""
        if request.user.is_authenticated:
            return None
            
        # Create a unique key based on path and query parameters
        key_parts = [request.path]
        if request.GET:
            # Sort query parameters for consistent keys
            sorted_params = sorted(request.GET.items())
            key_parts.extend([f"{k}={v}" for k, v in sorted_params])
            
        cache_key = hashlib.md5('|'.join(key_parts).encode()).hexdigest()
        return f"page_cache:{cache_key}"


class PerformanceMiddleware(MiddlewareMixin):
    """Middleware for performance monitoring and optimization"""
    
    def process_request(self, request):
        request.start_time = time.time()
        
        # Add request ID for tracking
        request.request_id = hashlib.md5(
            f"{request.path}{time.time()}".encode()
        ).hexdigest()[:8]
        
        return None
        
    def process_response(self, request, response):
        if hasattr(request, 'start_time'):
            duration = time.time() - request.start_time
            
            # Log slow requests
            if duration > 1.0:  # Log requests taking more than 1 second
                logger.warning(
                    f"Slow request: {request.path} took {duration:.2f}s "
                    f"(User: {request.user}, Method: {request.method})"
                )
                
            # Add performance headers
            response['X-Request-ID'] = getattr(request, 'request_id', 'unknown')
            response['X-Response-Time'] = f"{duration:.3f}s"
            
        return response


class SecurityMiddleware(MiddlewareMixin):
    """Enhanced security middleware"""
    
    def process_request(self, request):
        # Rate limiting check
        if self._is_rate_limited(request):
            return HttpResponse("Rate limit exceeded", status=429)
            
        # Security headers
        request.security_headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Referrer-Policy': 'strict-origin-when-cross-origin',
        }
        
        return None
        
    def process_response(self, request, response):
        # Add security headers
        if hasattr(request, 'security_headers'):
            for header, value in request.security_headers.items():
                response[header] = value
                
        return response
        
    def _is_rate_limited(self, request):
        """Simple rate limiting implementation"""
        if request.user.is_authenticated:
            return False
            
        # Rate limit anonymous users
        client_ip = self._get_client_ip(request)
        cache_key = f"rate_limit:{client_ip}"
        
        request_count = cache.get(cache_key, 0)
        if request_count > 100:  # 100 requests per minute
            return True
            
        cache.set(cache_key, request_count + 1, 60)  # 1 minute
        return False
        
    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class DatabaseOptimizationMiddleware(MiddlewareMixin):
    """Middleware for database query optimization"""
    
    def process_request(self, request):
        # Set database connection timeout
        from django.db import connection
        if connection.connection:
            connection.connection.set_timeout(30)  # 30 seconds
            
        return None
        
    def process_response(self, request, response):
        # Log database queries in debug mode
        if settings.DEBUG:
            from django.db import connection
            if connection.queries:
                total_time = sum(float(q['time']) for q in connection.queries)
                if total_time > 0.1:  # Log if total query time > 100ms
                    logger.warning(
                        f"Slow database queries: {len(connection.queries)} queries "
                        f"took {total_time:.3f}s for {request.path}"
                    )
                    
        return response


class SessionOptimizationMiddleware(MiddlewareMixin):
    """Middleware for session optimization"""
    
    def process_request(self, request):
        if request.user.is_authenticated:
            # Update session expiry
            request.session.set_expiry(3600)  # 1 hour
            
            # Store user info in session for quick access
            if 'user_info' not in request.session:
                request.session['user_info'] = {
                    'id': request.user.id,
                    'username': request.user.username,
                    'role': getattr(request.user, 'role', 'unknown'),
                    'last_activity': timezone.now().isoformat(),
                }
            else:
                # Update last activity
                request.session['user_info']['last_activity'] = timezone.now().isoformat()
                
        return None


class ErrorHandlingMiddleware(MiddlewareMixin):
    """Middleware for graceful error handling"""
    
    def process_exception(self, request, exception):
        # Log the exception
        logger.error(
            f"Exception in {request.path}: {str(exception)}",
            exc_info=True,
            extra={
                'request': request,
                'user': request.user,
                'request_id': getattr(request, 'request_id', 'unknown'),
            }
        )
        
        # Return custom error response
        if request.path.startswith('/api/'):
            return HttpResponse(
                '{"error": "Internal server error"}',
                status=500,
                content_type='application/json'
            )
        else:
            # Redirect to error page for web requests
            return redirect('error_500')
            
        return None 