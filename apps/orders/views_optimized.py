"""
Optimized views for Orders app
With caching and performance improvements
"""

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db.models import Prefetch, Q, Count, Sum
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_cookie
from django.views.generic import ListView, DetailView
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.conf import settings
import json
import logging

from .models import Order
from .serializers import OrderSerializer

logger = logging.getLogger(__name__)

# Кэширование на уровне views
CACHE_TIMEOUT = 300  # 5 минут
CACHE_LONG_TIMEOUT = 600  # 10 минут

@login_required
@cache_page(CACHE_TIMEOUT)
@vary_on_cookie
def orders_list_optimized(request):
    """
    Оптимизированный список заказов с кэшированием
    """
    try:
        # Получаем параметры фильтрации
        status_filter = request.GET.get('status', '')
        client_filter = request.GET.get('client', '')
        workshop_filter = request.GET.get('workshop', '')
        search_query = request.GET.get('search', '')
        
        # Создаем ключ кэша на основе параметров
        cache_key = f'orders_list_{status_filter}_{client_filter}_{workshop_filter}_{search_query}'
        
        # Пытаемся получить из кэша
        cached_result = cache.get(cache_key)
        if cached_result:
            orders_data, total_count = cached_result
        else:
            # Базовый QuerySet с оптимизацией
            queryset = Order.objects.select_related(
                'client', 'workshop', 'product'
            ).prefetch_related(
                'items__product',
                'stages'
            )
            
            # Применяем фильтры
            if status_filter:
                queryset = queryset.filter(status=status_filter)
            if client_filter:
                queryset = queryset.filter(client_id=client_filter)
            if workshop_filter:
                queryset = queryset.filter(workshop_id=workshop_filter)
            if search_query:
                queryset = queryset.filter(
                    Q(name__icontains=search_query) |
                    Q(client__name__icontains=search_query) |
                    Q(product__name__icontains=search_query)
                )
            
            # Сортируем по приоритету и дате
            queryset = queryset.order_by('-priority', '-created_at')
            
            # Пагинация
            page = request.GET.get('page', 1)
            paginator = Paginator(queryset, 50)  # 50 заказов на страницу
            
            try:
                orders_page = paginator.page(page)
            except:
                orders_page = paginator.page(1)
            
            # Сериализуем данные
            orders_data = OrderSerializer(orders_page.object_list, many=True).data
            total_count = paginator.count
            
            # Кэшируем результат
            cache.set(cache_key, (orders_data, total_count), CACHE_TIMEOUT)
        
        # Подготавливаем контекст
        context = {
            'orders': orders_data,
            'total_count': total_count,
            'status_filter': status_filter,
            'client_filter': client_filter,
            'workshop_filter': workshop_filter,
            'search_query': search_query,
        }
        
        return render(request, 'orders/orders.html', context)
        
    except Exception as e:
        logger.error(f"Error in orders_list_optimized: {e}")
        return render(request, 'orders/orders.html', {'error': 'Произошла ошибка при загрузке заказов'})

@login_required
@cache_page(CACHE_LONG_TIMEOUT)
@vary_on_cookie
def order_detail_optimized(request, order_id):
    """
    Оптимизированная детальная страница заказа с кэшированием
    """
    try:
        cache_key = f'order_detail_{order_id}'
        order_data = cache.get(cache_key)
        
        if order_data is None:
            # Получаем заказ с оптимизацией
            order = get_object_or_404(
                Order.objects.select_related(
                    'client', 'workshop', 'product'
                ).prefetch_related(
                    'items__product',
                    'stages__workshop',
                    'stages__employee'
                ),
                id=order_id
            )
            
            # Сериализуем данные
            order_data = OrderSerializer(order).data
            
            # Кэшируем на 10 минут
            cache.set(cache_key, order_data, CACHE_LONG_TIMEOUT)
        
        context = {
            'order': order_data,
        }
        
        return render(request, 'orders/order_detail.html', context)
        
    except Exception as e:
        logger.error(f"Error in order_detail_optimized: {e}")
        return render(request, 'orders/order_detail.html', {'error': 'Произошла ошибка при загрузке заказа'})

@login_required
def orders_api_optimized(request):
    """
    Оптимизированный API для заказов с кэшированием
    """
    try:
        # Получаем параметры
        status = request.GET.get('status', '')
        client_id = request.GET.get('client_id', '')
        limit = int(request.GET.get('limit', 100))
        
        # Создаем ключ кэша
        cache_key = f'orders_api_{status}_{client_id}_{limit}'
        
        # Пытаемся получить из кэша
        cached_result = cache.get(cache_key)
        if cached_result:
            return JsonResponse(cached_result)
        
        # Базовый QuerySet
        queryset = Order.objects.select_related(
            'client', 'workshop', 'product'
        ).prefetch_related(
            'items__product'
        )
        
        # Применяем фильтры
        if status:
            queryset = queryset.filter(status=status)
        if client_id:
            queryset = queryset.filter(client_id=client_id)
        
        # Ограничиваем количество
        queryset = queryset[:limit]
        
        # Сериализуем
        orders_data = OrderSerializer(queryset, many=True).data
        
        result = {
            'success': True,
            'orders': orders_data,
            'count': len(orders_data)
        }
        
        # Кэшируем результат
        cache.set(cache_key, result, CACHE_TIMEOUT)
        
        return JsonResponse(result)
        
    except Exception as e:
        logger.error(f"Error in orders_api_optimized: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Произошла ошибка при загрузке заказов'
        }, status=500)

@login_required
def orders_statistics_optimized(request):
    """
    Оптимизированная статистика по заказам с кэшированием
    """
    try:
        cache_key = 'orders_statistics'
        stats = cache.get(cache_key)
        
        if stats is None:
            # Получаем статистику
            total_orders = Order.objects.count()
            orders_by_status = Order.objects.values('status').annotate(
                count=Count('id')
            )
            
            # Статистика по приоритетам
            urgent_orders = Order.objects.filter(priority__gte=8).count()
            normal_orders = Order.objects.filter(priority__range=(4, 7)).count()
            low_priority_orders = Order.objects.filter(priority__lte=3).count()
            
            # Статистика по времени
            from django.utils import timezone
            now = timezone.now()
            today = now.date()
            week_ago = today - timezone.timedelta(days=7)
            month_ago = today - timezone.timedelta(days=30)
            
            orders_today = Order.objects.filter(created_at__date=today).count()
            orders_week = Order.objects.filter(created_at__date__gte=week_ago).count()
            orders_month = Order.objects.filter(created_at__date__gte=month_ago).count()
            
            stats = {
                'total_orders': total_orders,
                'orders_by_status': list(orders_by_status),
                'priority_stats': {
                    'urgent': urgent_orders,
                    'normal': normal_orders,
                    'low': low_priority_orders,
                },
                'time_stats': {
                    'today': orders_today,
                    'week': orders_week,
                    'month': orders_month,
                }
            }
            
            # Кэшируем на 10 минут
            cache.set(cache_key, stats, CACHE_LONG_TIMEOUT)
        
        return JsonResponse({
            'success': True,
            'statistics': stats
        })
        
    except Exception as e:
        logger.error(f"Error in orders_statistics_optimized: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Произошла ошибка при загрузке статистики'
        }, status=500)

# Оптимизированные классы-представления
@method_decorator(login_required, name='dispatch')
class OrdersListView(ListView):
    """
    Оптимизированный класс-представление для списка заказов
    """
    model = Order
    template_name = 'orders/orders.html'
    context_object_name = 'orders'
    paginate_by = 50
    
    def get_queryset(self):
        """Оптимизированный QuerySet"""
        queryset = Order.objects.select_related(
            'client', 'workshop', 'product'
        ).prefetch_related(
            'items__product',
            'stages'
        ).order_by('-priority', '-created_at')
        
        # Применяем фильтры
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        client_id = self.request.GET.get('client_id')
        if client_id:
            queryset = queryset.filter(client_id=client_id)
        
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(client__name__icontains=search)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        """Добавляем дополнительный контекст"""
        context = super().get_context_data(**kwargs)
        
        # Добавляем фильтры в контекст
        context['status_filter'] = self.request.GET.get('status', '')
        context['client_filter'] = self.request.GET.get('client_id', '')
        context['search_query'] = self.request.GET.get('search', '')
        
        return context

@method_decorator(login_required, name='dispatch')
class OrderDetailView(DetailView):
    """
    Оптимизированный класс-представление для детальной страницы заказа
    """
    model = Order
    template_name = 'orders/order_detail.html'
    context_object_name = 'order'
    
    def get_queryset(self):
        """Оптимизированный QuerySet"""
        return Order.objects.select_related(
            'client', 'workshop', 'product'
        ).prefetch_related(
            'items__product',
            'stages__workshop',
            'stages__employee'
        )

# Утилиты для очистки кэша
def clear_orders_cache():
    """Очищает весь кэш заказов"""
    cache_keys = [
        'orders_list_',
        'order_detail_',
        'orders_api_',
        'orders_statistics',
    ]
    
    # Получаем все ключи кэша и удаляем связанные с заказами
    for key in cache_keys:
        cache.delete_pattern(f'{key}*')
    
    logger.info("Orders cache cleared")

def clear_order_cache(order_id):
    """Очищает кэш конкретного заказа"""
    cache.delete(f'order_detail_{order_id}')
    logger.info(f"Order {order_id} cache cleared") 