from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.db.models import Q, Count
from django.utils import timezone
from django.core.paginator import Paginator
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, 
    DeleteView, TemplateView
)
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import JSONParser
from datetime import datetime, timedelta
import json

from .models import (
    Notification, NotificationType, NotificationTemplate,
    NotificationGroup, NotificationPreference, NotificationLog
)
from .serializers import (
    NotificationSerializer, NotificationTypeSerializer,
    NotificationTemplateSerializer, NotificationGroupSerializer,
    NotificationPreferenceSerializer, NotificationLogSerializer,
    BulkNotificationSerializer, NotificationStatsSerializer,
    MarkAsReadSerializer, NotificationFilterSerializer
)
from .utils import NotificationService


# ==================== DJANGO VIEWS ====================

class NotificationListView(LoginRequiredMixin, ListView):
    """Список уведомлений пользователя"""
    model = Notification
    template_name = 'notifications/notification_list.html'
    context_object_name = 'notifications'
    paginate_by = 20
    
    def get_queryset(self):
        return Notification.objects.filter(
            recipient=self.request.user
        ).select_related('notification_type').order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['unread_count'] = Notification.objects.filter(
            recipient=self.request.user,
            status='unread'
        ).count()
        context['notification_types'] = NotificationType.objects.filter(is_active=True)
        return context


class NotificationDetailView(LoginRequiredMixin, DetailView):
    """Детальное представление уведомления"""
    model = Notification
    template_name = 'notifications/notification_detail.html'
    context_object_name = 'notification'
    
    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)
    
    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        # Отмечаем уведомление как прочитанное
        notification = self.get_object()
        if notification.status == 'unread':
            notification.mark_as_read()
        return response


class NotificationSettingsView(LoginRequiredMixin, UpdateView):
    """Настройки уведомлений пользователя"""
    model = NotificationPreference
    template_name = 'notifications/notification_settings.html'
    fields = [
        'email_notifications', 'email_daily_digest', 'email_weekly_digest',
        'push_notifications', 'sms_notifications', 'quiet_hours_start',
        'quiet_hours_end'
    ]
    success_url = reverse_lazy('notifications:settings')
    
    def get_object(self):
        obj, created = NotificationPreference.objects.get_or_create(
            user=self.request.user
        )
        return obj
    
    def form_valid(self, form):
        messages.success(self.request, 'Настройки уведомлений обновлены')
        return super().form_valid(form)


class NotificationCreateView(LoginRequiredMixin, CreateView):
    """Создание нового уведомления"""
    model = Notification
    template_name = 'notifications/notification_form.html'
    fields = [
        'title', 'message', 'notification_type', 'recipient',
        'priority', 'action_url', 'action_text', 'expires_at'
    ]
    success_url = reverse_lazy('notifications:list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['notification_types'] = NotificationType.objects.filter(is_active=True)
        return context
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Уведомление создано')
        return super().form_valid(form)


class NotificationDashboardView(LoginRequiredMixin, TemplateView):
    """Дашборд уведомлений"""
    template_name = 'notifications/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Статистика
        context['total_notifications'] = Notification.objects.filter(
            recipient=user
        ).count()
        context['unread_count'] = Notification.objects.filter(
            recipient=user,
            status='unread'
        ).count()
        context['recent_notifications'] = Notification.objects.filter(
            recipient=user
        ).select_related('notification_type')[:10]
        
        # Уведомления по типам
        context['notifications_by_type'] = Notification.objects.filter(
            recipient=user
        ).values('notification_type__name').annotate(
            count=Count('id')
        )
        
        # Уведомления по приоритету
        context['notifications_by_priority'] = Notification.objects.filter(
            recipient=user
        ).values('priority').annotate(
            count=Count('id')
        )
        
        return context


# ==================== API VIEWSETS ====================

class NotificationViewSet(viewsets.ModelViewSet):
    """API для уведомлений"""
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = PageNumberPagination
    
    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)
    
    @action(detail=False, methods=['get'])
    def unread(self, request):
        """Получить непрочитанные уведомления"""
        unread_notifications = self.get_queryset().filter(status='unread')
        serializer = self.get_serializer(unread_notifications, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def mark_as_read(self, request):
        """Отметить уведомления как прочитанные"""
        serializer = MarkAsReadSerializer(data=request.data)
        if serializer.is_valid():
            notification_ids = serializer.validated_data.get('notification_ids', [])
            mark_all = serializer.validated_data.get('mark_all', False)
            
            if mark_all:
                # Отметить все как прочитанные
                self.get_queryset().filter(status='unread').update(
                    status='read',
                    read_at=timezone.now()
                )
                count = self.get_queryset().filter(status='unread').count()
            else:
                # Отметить конкретные уведомления
                notifications = self.get_queryset().filter(id__in=notification_ids)
                for notification in notifications:
                    notification.mark_as_read()
                count = len(notification_ids)
            
            return Response({
                'message': f'Отмечено как прочитанные: {count}',
                'marked_count': count
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Получить статистику уведомлений"""
        user = request.user
        queryset = self.get_queryset()
        
        stats = {
            'total_notifications': queryset.count(),
            'unread_count': queryset.filter(status='unread').count(),
            'read_count': queryset.filter(status='read').count(),
            'archived_count': queryset.filter(status='archived').count(),
            'notifications_by_type': queryset.values('notification_type__name').annotate(
                count=Count('id')
            ),
            'notifications_by_priority': queryset.values('priority').annotate(
                count=Count('id')
            ),
            'recent_notifications': NotificationSerializer(
                queryset[:5], many=True
            ).data
        }
        
        serializer = NotificationStatsSerializer(stats)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """Массовое создание уведомлений"""
        serializer = BulkNotificationSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            notification_service = NotificationService()
            
            created_count = notification_service.send_bulk_notifications(
                title=data['title'],
                message=data['message'],
                notification_type_id=data['notification_type_id'],
                recipient_ids=data['recipient_ids'],
                priority=data['priority'],
                action_url=data.get('action_url'),
                action_text=data.get('action_text'),
                expires_at=data.get('expires_at'),
                metadata=data.get('metadata', {})
            )
            
            return Response({
                'message': f'Создано уведомлений: {created_count}',
                'created_count': created_count
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class NotificationTypeViewSet(viewsets.ModelViewSet):
    """API для типов уведомлений"""
    queryset = NotificationType.objects.filter(is_active=True)
    serializer_class = NotificationTypeSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'code', 'description']
    ordering_fields = ['name', 'code']


class NotificationTemplateViewSet(viewsets.ModelViewSet):
    """API для шаблонов уведомлений"""
    queryset = NotificationTemplate.objects.filter(is_active=True)
    serializer_class = NotificationTemplateSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'title_template', 'message_template']
    ordering_fields = ['name', 'created_at']


class NotificationGroupViewSet(viewsets.ModelViewSet):
    """API для групп уведомлений"""
    queryset = NotificationGroup.objects.filter(is_active=True)
    serializer_class = NotificationGroupSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']


class NotificationPreferenceViewSet(viewsets.ModelViewSet):
    """API для настроек уведомлений"""
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return NotificationPreference.objects.filter(user=self.request.user)
    
    def get_object(self):
        obj, created = NotificationPreference.objects.get_or_create(
            user=self.request.user
        )
        return obj


# ==================== UTILITY VIEWS ====================

@login_required
def notification_bell(request):
    """Компонент колокольчика уведомлений"""
    unread_count = Notification.objects.filter(
        recipient=request.user,
        status='unread'
    ).count()
    
    recent_notifications = Notification.objects.filter(
        recipient=request.user
    ).select_related('notification_type')[:5]
    
    return render(request, 'notifications/notification_bell.html', {
        'unread_count': unread_count,
        'recent_notifications': recent_notifications
    })


@login_required
@require_http_methods(["POST"])
def mark_notification_read(request, notification_id):
    """Отметить уведомление как прочитанное"""
    try:
        notification = get_object_or_404(
            Notification,
            id=notification_id,
            recipient=request.user
        )
        notification.mark_as_read()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(["POST"])
def mark_all_notifications_read(request):
    """Отметить все уведомления как прочитанные"""
    try:
        Notification.objects.filter(
            recipient=request.user,
            status='unread'
        ).update(status='read', read_at=timezone.now())
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def notification_filters(request):
    """Фильтрация уведомлений"""
    serializer = NotificationFilterSerializer(data=request.GET)
    if serializer.is_valid():
        filters_data = serializer.validated_data
        
        queryset = Notification.objects.filter(recipient=request.user)
        
        # Применяем фильтры
        if filters_data.get('status'):
            queryset = queryset.filter(status=filters_data['status'])
        
        if filters_data.get('priority'):
            queryset = queryset.filter(priority=filters_data['priority'])
        
        if filters_data.get('notification_type_id'):
            queryset = queryset.filter(
                notification_type_id=filters_data['notification_type_id']
            )
        
        if filters_data.get('date_from'):
            queryset = queryset.filter(created_at__date__gte=filters_data['date_from'])
        
        if filters_data.get('date_to'):
            queryset = queryset.filter(created_at__date__lte=filters_data['date_to'])
        
        if filters_data.get('search'):
            search_term = filters_data['search']
            queryset = queryset.filter(
                Q(title__icontains=search_term) |
                Q(message__icontains=search_term)
            )
        
        # Пагинация
        page = filters_data.get('page', 1)
        page_size = filters_data.get('page_size', 20)
        paginator = Paginator(queryset, page_size)
        notifications_page = paginator.get_page(page)
        
        serializer = NotificationSerializer(notifications_page, many=True)
        return JsonResponse({
            'notifications': serializer.data,
            'total_pages': paginator.num_pages,
            'current_page': page,
            'total_count': paginator.count
        })
    
    return JsonResponse({'error': 'Invalid filters'}, status=400)


@login_required
def notification_export(request):
    """Экспорт уведомлений"""
    from django.http import HttpResponse
    import csv
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="notifications.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'ID', 'Заголовок', 'Сообщение', 'Тип', 'Приоритет', 
        'Статус', 'Дата создания', 'Дата прочтения'
    ])
    
    notifications = Notification.objects.filter(
        recipient=request.user
    ).select_related('notification_type')
    
    for notification in notifications:
        writer.writerow([
            notification.id,
            notification.title,
            notification.message,
            notification.notification_type.name,
            notification.get_priority_display(),
            notification.get_status_display(),
            notification.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            notification.read_at.strftime('%Y-%m-%d %H:%M:%S') if notification.read_at else ''
        ])
    
    return response


# ==================== ADMIN VIEWS ====================

class AdminNotificationListView(LoginRequiredMixin, ListView):
    """Административный список всех уведомлений"""
    model = Notification
    template_name = 'notifications/admin_notification_list.html'
    context_object_name = 'notifications'
    paginate_by = 50
    
    def get_queryset(self):
        queryset = Notification.objects.select_related(
            'recipient', 'notification_type'
        ).order_by('-created_at')
        
        # Фильтры
        status_filter = self.request.GET.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        priority_filter = self.request.GET.get('priority')
        if priority_filter:
            queryset = queryset.filter(priority=priority_filter)
        
        type_filter = self.request.GET.get('type')
        if type_filter:
            queryset = queryset.filter(notification_type_id=type_filter)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['notification_types'] = NotificationType.objects.filter(is_active=True)
        context['status_choices'] = Notification.STATUS_CHOICES
        context['priority_choices'] = Notification.PRIORITY_CHOICES
        return context


class AdminNotificationCreateView(LoginRequiredMixin, CreateView):
    """Административное создание уведомлений"""
    model = Notification
    template_name = 'notifications/admin_notification_form.html'
    fields = [
        'title', 'message', 'notification_type', 'recipient',
        'priority', 'action_url', 'action_text', 'expires_at'
    ]
    success_url = reverse_lazy('notifications:admin_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['notification_types'] = NotificationType.objects.filter(is_active=True)
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Уведомление создано')
        return super().form_valid(form) 


class NotificationsComingSoonView(TemplateView):
    template_name = 'notifications/coming_soon.html'

    def get_template_names(self):
        ua = self.request.META.get('HTTP_USER_AGENT', '').lower()
        is_mobile = any(k in ua for k in ['iphone', 'android', 'mobile'])
        if is_mobile:
            return ['notifications/coming_soon_mobile.html']
        return ['notifications/coming_soon.html'] 