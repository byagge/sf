from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from .models import AttendanceRecord
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Q, Count
from datetime import datetime, timedelta
import json
from django.views.decorators.csrf import ensure_csrf_cookie

User = get_user_model()

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def checkin_by_qr(request):
    try:
        data = request.data
        employee = None
        employee_id = data.get('employee_id')
        if not employee_id and 'qr' in data:
            qr_data = data['qr']
            if qr_data == 'ATTENDANCE_CHECKIN':
                employee = request.user
            else:
                # Можно добавить другие типы QR-кодов
                return Response({'error': 'Некорректный QR-код'}, status=status.HTTP_400_BAD_REQUEST)
        elif employee_id:
            employee = User.objects.get(id=employee_id)
        else:
            return Response({'error': 'Не передан employee_id'}, status=status.HTTP_400_BAD_REQUEST)

        # Проверяем, не отмечался ли уже сегодня
        today = timezone.localdate()
        current_time = timezone.now()
        
        record, created = AttendanceRecord.objects.get_or_create(
            employee=employee,
            date=today,
            defaults={'check_in': current_time}
        )
        
        if not created:
            # Если запись уже существует, обновляем время прихода
            record.check_in = current_time
            record.save()  # Это вызовет calculate_penalty() и обновит штрафы
            
            return Response({
                'detail': 'Время прихода обновлено', 
                'record_id': record.id,
                'check_in': record.check_in,
                'is_late': record.is_late,
                'penalty_amount': float(record.penalty_amount)
            }, status=200)
        
        # Для новой записи штраф уже рассчитан в save()
        return Response({
            'success': True, 
            'record_id': record.id, 
            'check_in': record.check_in,
            'is_late': record.is_late,
            'penalty_amount': float(record.penalty_amount)
        }, status=201)
    except User.DoesNotExist:
        return Response({'error': 'Сотрудник не найден'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def checkout_employee(request):
    """Отметка ухода сотрудника"""
    try:
        data = request.data
        employee_id = data.get('employee_id')
        if not employee_id:
            return Response({'error': 'Не передан employee_id'}, status=status.HTTP_400_BAD_REQUEST)
        
        employee = User.objects.get(id=employee_id)
        today = timezone.localdate()
        
        try:
            record = AttendanceRecord.objects.get(employee=employee, date=today)
            if record.check_out:
                return Response({'detail': 'Сотрудник уже отмечен как ушедший сегодня'}, status=200)
            
            record.check_out = timezone.now()
            record.save()
            return Response({'success': True, 'check_out': record.check_out}, status=200)
        except AttendanceRecord.DoesNotExist:
            return Response({'error': 'Сотрудник не отмечался сегодня'}, status=404)
            
    except User.DoesNotExist:
        return Response({'error': 'Сотрудник не найден'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def attendance_overview(request):
    """Обзор посещаемости для дашборда"""
    try:
        today = timezone.localdate()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        # Статистика за сегодня
        today_records = AttendanceRecord.objects.filter(date=today)
        present_today = today_records.count()
        checked_out_today = today_records.filter(check_out__isnull=False).count()
        late_today = today_records.filter(is_late=True).count()
        total_penalties_today = sum(record.penalty_amount for record in today_records)
        
        # Статистика за неделю
        week_records = AttendanceRecord.objects.filter(date__gte=week_ago)
        week_attendance = week_records.count()
        week_late = week_records.filter(is_late=True).count()
        week_penalties = sum(record.penalty_amount for record in week_records)
        
        # Статистика за месяц
        month_records = AttendanceRecord.objects.filter(date__gte=month_ago)
        month_attendance = month_records.count()
        month_late = month_records.filter(is_late=True).count()
        month_penalties = sum(record.penalty_amount for record in month_records)
        
        # Топ сотрудников по посещаемости
        top_employees = User.objects.annotate(
            attendance_count=Count('attendance_records')
        ).order_by('-attendance_count')[:5]
        
        top_employees_data = []
        for emp in top_employees:
            top_employees_data.append({
                'id': emp.id,
                'name': emp.get_full_name() or emp.username,
                'attendance_count': emp.attendance_count,
                'avatar': emp.get_full_name() and emp.get_full_name()[0].upper() or emp.username[0].upper()
            })
        
        return Response({
            'today': {
                'present': present_today,
                'checked_out': checked_out_today,
                'late': late_today,
                'total_penalties': float(total_penalties_today),
                'total_employees': User.objects.count()
            },
            'week': {
                'attendance': week_attendance,
                'late': week_late,
                'total_penalties': float(week_penalties)
            },
            'month': {
                'attendance': month_attendance,
                'late': month_late,
                'total_penalties': float(month_penalties)
            },
            'top_employees': top_employees_data
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def attendance_list(request):
    """Список записей посещаемости с фильтрацией"""
    try:
        # Параметры фильтрации
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        employee_id = request.GET.get('employee_id')
        status_filter = request.GET.get('status')  # present, absent, checked_out
        
        # Базовый queryset
        records = AttendanceRecord.objects.select_related('employee').all()
        
        # Применяем фильтры
        if date_from:
            try:
                date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
                records = records.filter(date__gte=date_from)
            except ValueError:
                pass
                
        if date_to:
            try:
                date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
                records = records.filter(date__lte=date_to)
            except ValueError:
                pass
                
        if employee_id:
            records = records.filter(employee_id=employee_id)
            
        if status_filter:
            if status_filter == 'present':
                records = records.filter(check_out__isnull=True)
            elif status_filter == 'checked_out':
                records = records.filter(check_out__isnull=False)
        
        # Сортируем по дате и времени
        records = records.order_by('-date', '-check_in')
        
        # Пагинация
        page = int(request.GET.get('page', 1))
        per_page = int(request.GET.get('per_page', 20))
        start = (page - 1) * per_page
        end = start + per_page
        
        total = records.count()
        records_page = records[start:end]
        
        # Формируем данные для ответа
        records_data = []
        for record in records_page:
            # Конвертируем время в местное время для отображения
            local_check_in = timezone.localtime(record.check_in) if record.check_in else None
            local_check_out = timezone.localtime(record.check_out) if record.check_out else None
            
            records_data.append({
                'id': record.id,
                'employee': {
                    'id': record.employee.id,
                    'name': record.employee.get_full_name() or record.employee.username,
                    'avatar': record.employee.get_full_name() and record.employee.get_full_name()[0].upper() or record.employee.username[0].upper()
                },
                'date': record.date.isoformat(),
                'check_in': local_check_in.isoformat() if local_check_in else None,
                'check_out': local_check_out.isoformat() if local_check_out else None,
                'status': 'checked_out' if record.check_out else 'present',
                'note': record.note or '',
                'is_late': record.is_late,
                'penalty_amount': float(record.penalty_amount)
            })
        
        return Response({
            'records': records_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def recalculate_today_penalties(request):
    """Принудительно пересчитывает штрафы за сегодня"""
    try:
        today = timezone.localdate()
        today_records = AttendanceRecord.objects.filter(date=today)
        
        updated_count = 0
        for record in today_records:
            if record.recalculate_penalty():
                updated_count += 1
                record.save()
        
        return Response({
            'success': True,
            'message': f'Штрафы пересчитаны для {updated_count} записей',
            'updated_count': updated_count
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@ensure_csrf_cookie
def qr_scanner_page(request):
    return render(request, 'qr_scanner.html')

def attendance_page(request):
    """Основная страница посещаемости"""
    return render(request, 'attendance/attendance.html')
