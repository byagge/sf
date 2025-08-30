from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import time
from apps.attendance.models import AttendanceRecord


class Command(BaseCommand):
    help = 'Автоматически отмечает уход всех сотрудников после 18:00'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Принудительно выполнить команду независимо от времени',
        )

    def handle(self, *args, **options):
        current_time = timezone.now()
        local_time = timezone.localtime(current_time)
        
        # Проверяем время (если не указан флаг --force)
        if not options['force'] and local_time.time() < time(18, 0):
            self.stdout.write(
                self.style.WARNING(
                    f'Текущее время {local_time.strftime("%H:%M")} раньше 18:00. '
                    'Используйте --force для принудительного выполнения.'
                )
            )
            return
        
        today = timezone.localdate()
        
        # Находим всех сотрудников, которые пришли, но не ушли
        active_records = AttendanceRecord.objects.filter(
            date=today,
            check_in__isnull=False,
            check_out__isnull=True
        )
        
        if not active_records.exists():
            self.stdout.write(
                self.style.SUCCESS('Нет сотрудников для автоматической отметки ухода')
            )
            return
        
        checked_out_count = 0
        for record in active_records:
            record.check_out = current_time
            record.save()
            checked_out_count += 1
            self.stdout.write(
                f'Отмечен уход для {record.employee.get_full_name() or record.employee.username}'
            )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Успешно отмечен уход для {checked_out_count} сотрудников в {local_time.strftime("%H:%M")}'
            )
        ) 