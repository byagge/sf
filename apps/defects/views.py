from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.views import View
from django.shortcuts import render
from django.db.models import Q
from django.contrib.auth import get_user_model

from .models import Defect
from .serializers import (
    DefectSerializer, 
    DefectConfirmationSerializer, 
    DefectRepairSerializer,
    DefectListSerializer
)

User = get_user_model()

class DefectViewSet(viewsets.ModelViewSet):
    queryset = Defect.objects.select_related('product', 'user', 'confirmed_by', 'target_workshop').all().order_by('-created_at')
    serializer_class = DefectSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Фильтрует браки в зависимости от роли пользователя"""
        user = self.request.user
        
        if user.role == User.Role.MASTER:
            # Мастер видит браки только в своем цехе
            if user.workshop:
                return self.queryset.filter(
                    Q(user__workshop=user.workshop) |  # Браки сотрудников его цеха
                    Q(target_workshop=user.workshop)    # Браки, переведенные в его цех
                )
            else:
                return Defect.objects.none()
        elif user.role in [User.Role.FOUNDER, User.Role.DIRECTOR, User.Role.ADMIN]:
            # Администраторы видят все браки
            return self.queryset
        else:
            # Обычные сотрудники видят только свои браки
            return self.queryset.filter(user=user)
    
    def get_serializer_class(self):
        if self.action == 'list':
            return DefectListSerializer
        return DefectSerializer
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def confirm(self, request, pk=None):
        """Подтверждение брака мастером"""
        defect = self.get_object()
        user = request.user
        
        if user.role != User.Role.MASTER:
            return Response(
                {'error': 'Только мастер может подтверждать браки'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        if not defect.can_be_confirmed_by(user):
            return Response(
                {'error': 'Мастер не может подтвердить этот брак'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = DefectConfirmationSerializer(data=request.data)
        if serializer.is_valid():
            try:
                defect.confirm_defect(
                    master=user,
                    is_repairable=serializer.validated_data['is_repairable'],
                    defect_type=serializer.validated_data.get('defect_type'),
                    target_workshop=serializer.validated_data.get('target_workshop_id'),
                    comment=serializer.validated_data.get('comment', '')
                )
                return Response(
                    {'message': 'Брак успешно подтвержден', 'defect': DefectSerializer(defect).data},
                    status=status.HTTP_200_OK
                )
            except ValueError as e:
                return Response(
                    {'error': str(e)}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def mark_repaired(self, request, pk=None):
        """Отметить брак как починенный"""
        defect = self.get_object()
        user = request.user
        
        # Проверяем права: может ли пользователь отмечать брак как починенный
        can_repair = False
        if defect.repair_task and defect.repair_task.employee == user:
            can_repair = True
        elif user.role == User.Role.MASTER and defect.target_workshop and defect.target_workshop.manager == user:
            can_repair = True
        
        if not can_repair:
            return Response(
                {'error': 'У вас нет прав для отметки этого брака как починенного'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = DefectRepairSerializer(data=request.data)
        if serializer.is_valid():
            defect.mark_as_repaired(
                comment=serializer.validated_data.get('comment', '')
            )
            return Response(
                {'message': 'Брак отмечен как починенный', 'defect': DefectSerializer(defect).data},
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def close(self, request, pk=None):
        """Закрыть брак"""
        defect = self.get_object()
        user = request.user
        
        # Только мастер или администратор может закрыть брак
        if user.role not in [User.Role.MASTER, User.Role.ADMIN, User.Role.DIRECTOR, User.Role.FOUNDER]:
            return Response(
                {'error': 'У вас нет прав для закрытия брака'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        defect.close_defect()
        return Response(
            {'message': 'Брак закрыт', 'defect': DefectSerializer(defect).data},
            status=status.HTTP_200_OK
        )

class DefectStatsAPIView(APIView):
    """API для получения статистики браков"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        if user.role == User.Role.MASTER:
            # Статистика для мастера (только его цех)
            if user.workshop:
                defects = Defect.objects.filter(
                    Q(user__workshop=user.workshop) | Q(target_workshop=user.workshop)
                )
            else:
                defects = Defect.objects.none()
        elif user.role in [User.Role.FOUNDER, User.Role.DIRECTOR, User.Role.ADMIN]:
            # Статистика для администраторов (все браки)
            defects = Defect.objects.all()
        else:
            # Статистика для обычных сотрудников (только их браки)
            defects = Defect.objects.filter(user=user)
        
        stats = {
            'total_defects': defects.count(),
            'pending_confirmation': defects.filter(status=Defect.DefectStatus.PENDING).count(),
            'confirmed': defects.filter(status=Defect.DefectStatus.CONFIRMED).count(),
            'repairable': defects.filter(status=Defect.DefectStatus.REPAIRABLE).count(),
            'irreparable': defects.filter(status=Defect.DefectStatus.IRREPARABLE).count(),
            'transferred': defects.filter(status=Defect.DefectStatus.TRANSFERRED).count(),
            'repaired': defects.filter(status=Defect.DefectStatus.REPAIRED).count(),
            'closed': defects.filter(status=Defect.DefectStatus.CLOSED).count(),
            'unique_products': defects.values('product').distinct().count(),
            'unique_users': defects.values('user').distinct().count(),
        }
        
        return Response(stats)

class DefectPageView(View):
    def get(self, request):
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        is_mobile = any(m in user_agent for m in ['android', 'iphone', 'ipad', 'mobile'])
        template = 'defects_mobile.html' if is_mobile else 'defects.html'
        return render(request, template) 