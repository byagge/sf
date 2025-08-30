from celery import shared_task
from django.utils import timezone
from datetime import time
from .models import AttendanceRecord


@shared_task
def auto_checkout_after_6pm():
    """
    Автоматически отмечает уход всех сотрудников после 18:00
    Эта задача должна выполняться каждый день в 18:00
    """
    current_time = timezone.now()
    local_time = timezone.localtime(current_time)
    
    # Проверяем, что время после 18:00
    if local_time.time() < time(18, 0):
        return {
            'status': 'skipped',
            'message': f'Текущее время {local_time.strftime("%H:%M")} раньше 18:00',
            'checked_out_count': 0
        }
    
    today = timezone.localdate()
    
    # Находим всех сотрудников, которые пришли, но не ушли
    active_records = AttendanceRecord.objects.filter(
        date=today,
        check_in__isnull=False,
        check_out__isnull=True
    )
    
    if not active_records.exists():
        return {
            'status': 'success',
            'message': 'Нет сотрудников для автоматической отметки ухода',
            'checked_out_count': 0
        }
    
    checked_out_count = 0
    for record in active_records:
        record.check_out = current_time
        record.save()
        checked_out_count += 1
    
    return {
        'status': 'success',
        'message': f'Автоматически отмечен уход для {checked_out_count} сотрудников',
        'checked_out_count': checked_out_count,
        'checkout_time': current_time.isoformat()
    }


@shared_task
def cleanup_old_attendance_records():
    """
    Очищает старые записи посещаемости (старше 1 года)
    """
    from datetime import timedelta
    
    cutoff_date = timezone.localdate() - timedelta(days=365)
    deleted_count = AttendanceRecord.objects.filter(date__lt=cutoff_date).delete()[0]
    
    return {
        'status': 'success',
        'message': f'Удалено {deleted_count} старых записей посещаемости',
        'deleted_count': deleted_count
    }


@shared_task
def recalculate_today_penalties():
    """
    Пересчитывает штрафы за сегодняшний день
    """
    today = timezone.localdate()
    today_records = AttendanceRecord.objects.filter(date=today)
    
    updated_count = 0
    for record in today_records:
        if record.recalculate_penalty():
            updated_count += 1
            record.save()
    
    return {
        'status': 'success',
        'message': f'Штрафы пересчитаны для {updated_count} записей',
        'updated_count': updated_count
    } 