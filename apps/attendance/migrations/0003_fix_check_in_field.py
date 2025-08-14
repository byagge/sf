# Generated manually to fix check_in field and recalculate penalties

from django.db import migrations, models
from django.utils import timezone
from datetime import time

def recalculate_penalties(apps, schema_editor):
    """Пересчитывает штрафы для всех существующих записей с учетом часовых поясов"""
    AttendanceRecord = apps.get_model('attendance', 'AttendanceRecord')
    
    for record in AttendanceRecord.objects.all():
        # Рассчитываем штраф заново с учетом местного времени
        work_start_time = time(9, 0)
        
        # Конвертируем UTC время в местное время
        local_check_in = timezone.localtime(record.check_in)
        check_in_time = local_check_in.time()
        
        if check_in_time > work_start_time:
            record.is_late = True
            record.penalty_amount = 500.00
        else:
            record.is_late = False
            record.penalty_amount = 0.00
        
        record.save()

def reverse_recalculate_penalties(apps, schema_editor):
    """Откатывает изменения штрафов"""
    AttendanceRecord = apps.get_model('attendance', 'AttendanceRecord')
    
    for record in AttendanceRecord.objects.all():
        record.is_late = False
        record.penalty_amount = 0.00
        record.save()

class Migration(migrations.Migration):

    dependencies = [
        ('attendance', '0002_attendancerecord_is_late_and_more'),
    ]

    operations = [
        # Изменяем поле check_in - убираем auto_now_add
        migrations.AlterField(
            model_name='attendancerecord',
            name='check_in',
            field=models.DateTimeField(verbose_name='Время прихода'),
        ),
        
        # Запускаем функцию для пересчета штрафов
        migrations.RunPython(
            recalculate_penalties,
            reverse_recalculate_penalties
        ),
    ] 