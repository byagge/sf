from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.views import View
from django.shortcuts import render
from django.db import transaction
from django.utils import timezone
from .models import Defect, DefectRepairTask
from .serializers import (
    DefectSerializer, DefectRepairTaskSerializer, 
    DefectMasterReviewSerializer, DefectRepairTaskCreateSerializer
)
from apps.users.models import User

class DefectViewSet(viewsets.ModelViewSet):
    queryset = Defect.objects.select_related('product', 'user', 'master_confirmed_by', 'target_workshop').all().order_by('-created_at')
    serializer_class = DefectSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Фильтруем браки в зависимости от роли пользователя"""
        user = self.request.user
        
        if user.role == User.Role.MASTER:
            # Мастер видит браки только своего цеха
            return self.queryset.filter(user__workshop=user.workshop)
        elif user.role == User.Role.WORKER:
            # Рабочий видит только свои браки
            return self.queryset.filter(user=user)
        elif user.role in [User.Role.ADMIN, User.Role.DIRECTOR, User.Role.FOUNDER]:
            # Администраторы видят все браки
            return self.queryset
        else:
            # Остальные роли не видят браки
            return Defect.objects.none()

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def confirm_by_master(self, request, pk=None):
        """Подтверждение брака мастером"""
        defect = self.get_object()
        user = request.user
        
        if user.role != User.Role.MASTER:
            return Response(
                {'error': 'Только мастер может подтверждать браки'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        if not defect.can_master_review(user):
            return Response(
                {'error': 'Вы не можете подтвердить этот брак'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            defect.confirm_by_master(user)
            return Response({'message': 'Брак подтвержден мастером'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def review_defect(self, request, pk=None):
        """Полная проверка брака мастером"""
        defect = self.get_object()
        user = request.user
        
        if user.role != User.Role.MASTER:
            return Response(
                {'error': 'Только мастер может проверять браки'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        if not defect.can_master_review(user):
            return Response(
                {'error': 'Вы не можете проверить этот брак'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = DefectMasterReviewSerializer(data=request.data)
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    # Подтверждаем брак мастером
                    defect.confirm_by_master(user)
                    
                    can_be_fixed = serializer.validated_data['can_be_fixed']
                    defect.set_repairability(can_be_fixed)
                    
                    if not can_be_fixed:
                        # Если нельзя починить, устанавливаем тип брака
                        defect_type = serializer.validated_data.get('defect_type')
                        if defect_type:
                            defect.set_defect_type(defect_type)
                    else:
                        # Если можно починить, отправляем в цех для восстановления
                        target_workshop_id = serializer.validated_data.get('target_workshop_id')
                        if target_workshop_id:
                            defect.send_to_workshop(target_workshop_id)
                            
                            # Создаем задачу по восстановлению
                            DefectRepairTask.objects.create(
                                defect=defect,
                                workshop=target_workshop_id,
                                title=f"Восстановление брака по заказу {defect.product.order.id if hasattr(defect.product, 'order') else 'N/A'}",
                                description=f"Восстановление брака продукта {defect.product.name}",
                                priority='medium'
                            )
                    
                    # Обновляем примечания
                    notes = serializer.validated_data.get('notes')
                    if notes:
                        defect.notes = notes
                        defect.save()
                    
                    return Response({'message': 'Брак успешно проверен'})
                    
            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def mark_as_fixed(self, request, pk=None):
        """Отмечает брак как исправленный"""
        defect = self.get_object()
        user = request.user
        
        if defect.status != Defect.DefectStatus.SENT_TO_WORKSHOP:
            return Response(
                {'error': 'Брак должен быть отправлен в цех для восстановления'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            defect.mark_as_fixed(user)
            return Response({'message': 'Брак отмечен как исправленный'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class DefectRepairTaskViewSet(viewsets.ModelViewSet):
    queryset = DefectRepairTask.objects.select_related('defect', 'assigned_to', 'workshop').all().order_by('-created_at')
    serializer_class = DefectRepairTaskSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Фильтруем задачи в зависимости от роли пользователя"""
        user = self.request.user
        
        if user.role == User.Role.MASTER:
            # Мастер видит задачи своего цеха
            return self.queryset.filter(workshop=user.workshop)
        elif user.role == User.Role.WORKER:
            # Рабочий видит только назначенные на него задачи
            return self.queryset.filter(assigned_to=user)
        elif user.role in [User.Role.ADMIN, User.Role.DIRECTOR, User.Role.FOUNDER]:
            # Администраторы видят все задачи
            return self.queryset
        else:
            # Остальные роли не видят задачи
            return DefectRepairTask.objects.none()

    def create(self, request, *args, **kwargs):
        """Создание новой задачи по восстановлению брака"""
        serializer = DefectRepairTaskCreateSerializer(data=request.data)
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    task = serializer.save()
                    return Response(
                        DefectRepairTaskSerializer(task).data, 
                        status=status.HTTP_201_CREATED
                    )
            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def start_work(self, request, pk=None):
        """Начинает работу над задачей"""
        task = self.get_object()
        user = request.user
        
        if task.assigned_to and task.assigned_to != user:
            return Response(
                {'error': 'Только назначенный сотрудник может начинать работу'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            task.start_work()
            return Response({'message': 'Работа над задачей начата'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def complete_task(self, request, pk=None):
        """Завершает задачу"""
        task = self.get_object()
        user = request.user
        
        if task.assigned_to and task.assigned_to != user:
            return Response(
                {'error': 'Только назначенный сотрудник может завершать задачу'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            task.complete_task()
            return Response({'message': 'Задача завершена'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class DefectPageView(View):
    def get(self, request):
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        is_mobile = any(m in user_agent for m in ['android', 'iphone', 'ipad', 'mobile'])
        template = 'defects_mobile.html' if is_mobile else 'defects.html'
        return render(request, template) 