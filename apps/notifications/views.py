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
    template_name = 'notifications/mobile.html'
    context_object_name = 'notifications'
    paginate_by = 20
    
    def get_queryset(self):
        return Notification.objects.filter(
            user=self.request.user
        ).order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['unread_count'] = Notification.objects.filter(
            user=self.request.user,
            is_read=False
        ).count()
        context['page_title'] = 'Уведомления'
        return context


class NotificationDetailView(LoginRequiredMixin, DetailView):
    """Детальное представление уведомления"""
    model = Notification
    template_name = 'notifications/notification_detail.html'
    context_object_name = 'notification'
    
    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)
    
    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        # Отмечаем уведомление как прочитанное
        notification = self.get_object()
        if not notification.is_read:
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
        'title', 'message', 'notification_type'
    ]
    success_url = reverse_lazy('notifications:list')
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, 'Уведомление создано')
        return super().form_valid(form)


class NotificationDashboardView(LoginRequiredMixin, TemplateView):
    """Дашборд уведомлений"""
    template_name = 'notifications/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Статистика (упрощенная под текущую модель)
        context['total_notifications'] = Notification.objects.filter(
            user=user
        ).count()
        context['unread_count'] = Notification.objects.filter(
            user=user,
            is_read=False
        ).count()
        context['recent_notifications'] = Notification.objects.filter(
            user=user
        )[:10]
        
        return context


# ==================== API VIEWSETS ====================

class NotificationViewSet(viewsets.ModelViewSet):
    """API для уведомлений"""
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = PageNumberPagination
    
    def get_queryset(self):
        # Приводим к текущей модели: используем is_read
        return Notification.objects.filter(user=self.request.user).order_by('-created_at', 'id')
    
    @action(detail=False, methods=['get'])
    def unread(self, request):
        """Получить непрочитанные уведомления"""
        unread_notifications = self.get_queryset().filter(is_read=False)
        serializer = self.get_serializer(unread_notifications, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def mark_as_read(self, request):
        """Отметить уведомления как прочитанные"""
        ids = request.data if isinstance(request.data, list) else request.data.get('ids', [])
        qs = self.get_queryset().filter(id__in=ids)
        for n in qs:
            n.mark_as_read()
        return Response({'marked_count': qs.count()})


class NotificationTypeViewSet(viewsets.ModelViewSet):
	"""API для типов уведомлений"""
	queryset = NotificationType.objects.filter(is_active=True).order_by('name', 'id')
	serializer_class = NotificationTypeSerializer
	permission_classes = [IsAuthenticated]
	filter_backends = [filters.SearchFilter, filters.OrderingFilter]
	search_fields = ['name', 'code', 'description']
	ordering_fields = ['name', 'code']


class NotificationTemplateViewSet(viewsets.ModelViewSet):
	"""API для шаблонов уведомлений"""
	queryset = NotificationTemplate.objects.filter(is_active=True).order_by('name', 'id')
	serializer_class = NotificationTemplateSerializer
	permission_classes = [IsAuthenticated]
	filter_backends = [filters.SearchFilter, filters.OrderingFilter]
	search_fields = ['name', 'title_template', 'message_template']
	ordering_fields = ['name', 'created_at']


class NotificationGroupViewSet(viewsets.ModelViewSet):
	"""API для групп уведомлений"""
	queryset = NotificationGroup.objects.filter(is_active=True).order_by('name', 'id')
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
		return NotificationPreference.objects.filter(user=self.request.user).order_by('-created_at', 'id')
	
	def get_object(self):
		obj, created = NotificationPreference.objects.get_or_create(
			user=self.request.user
		)
		return obj


# ==================== UTILITY VIEWS ====================

@login_required
def notification_bell(request):
    """Страница уведомлений (мобильная)"""
    unread_count = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).count()
    
    notifications = Notification.objects.filter(
        user=request.user
    ).order_by('-created_at')[:50]
    
    return render(request, 'notifications/mobile.html', {
        'unread_count': unread_count,
        'notifications': notifications,
        'page_title': 'Уведомления'
    })


@login_required
@require_http_methods(["GET"])
def unread_count(request):
    """Простой endpoint для получения количества непрочитанных уведомлений"""
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({'unread_count': count}) 