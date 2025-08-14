from django.core.management.base import BaseCommand
from apps.attendance.models import AttendanceRecord
from django.db import transaction


class Command(BaseCommand):
    help = 'Пересчитывает штрафы для всех существующих записей посещаемости'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Показать что будет изменено без внесения изменений',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # Получаем все записи с опозданиями (после 9:00)
        late_records = []
        on_time_records = []
        
        for record in AttendanceRecord.objects.all():
            if record.check_in.time().hour >= 9:
                if not record.is_late or record.penalty_amount == 0:
                    late_records.append(record)
            else:
                if record.is_late or record.penalty_amount > 0:
                    on_time_records.append(record)
        
        self.stdout.write(f"Найдено записей с опозданиями: {len(late_records)}")
        self.stdout.write(f"Найдено записей вовремя: {len(on_time_records)}")
        
        if dry_run:
            self.stdout.write("\n=== РЕЖИМ ПРЕДВАРИТЕЛЬНОГО ПРОСМОТРА ===")
            
            if late_records:
                self.stdout.write("\nЗаписи, которые получат штраф:")
                for record in late_records[:10]:  # Показываем первые 10
                    self.stdout.write(
                        f"  {record.employee.get_full_name()} - {record.date} {record.check_in.time()}"
                    )
                if len(late_records) > 10:
                    self.stdout.write(f"  ... и еще {len(late_records) - 10} записей")
            
            if on_time_records:
                self.stdout.write("\nЗаписи, с которых снимут штраф:")
                for record in on_time_records[:10]:  # Показываем первые 10
                    self.stdout.write(
                        f"  {record.employee.get_full_name()} - {record.date} {record.check_in.time()}"
                    )
                if len(on_time_records) > 10:
                    self.stdout.write(f"  ... и еще {len(on_time_records) - 10} записей")
            
            self.stdout.write("\nДля применения изменений запустите команду без --dry-run")
            return
        
        # Применяем изменения
        with transaction.atomic():
            updated_count = 0
            
            # Обновляем записи с опозданиями
            for record in late_records:
                old_penalty = record.penalty_amount
                old_is_late = record.is_late
                
                record.calculate_penalty()
                record.save()
                
                if old_penalty != record.penalty_amount or old_is_late != record.is_late:
                    updated_count += 1
                    self.stdout.write(
                        f"✓ {record.employee.get_full_name()} - {record.date} {record.check_in.time()}: "
                        f"штраф {old_penalty} → {record.penalty_amount}, опоздание {old_is_late} → {record.is_late}"
                    )
            
            # Обновляем записи вовремя
            for record in on_time_records:
                old_penalty = record.penalty_amount
                old_is_late = record.is_late
                
                record.calculate_penalty()
                record.save()
                
                if old_penalty != record.penalty_amount or old_is_late != record.is_late:
                    updated_count += 1
                    self.stdout.write(
                        f"✓ {record.employee.get_full_name()} - {record.date} {record.check_in.time()}: "
                        f"штраф {old_penalty} → {record.penalty_amount}, опоздание {old_is_late} → {record.is_late}"
                    )
        
        self.stdout.write(f"\n✅ Обновлено записей: {updated_count}")
        self.stdout.write("Штрафы успешно пересчитаны!") 