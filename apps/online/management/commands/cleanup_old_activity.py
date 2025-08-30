from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from apps.online.models import UserActivity

class Command(BaseCommand):
    help = 'Очищает старые записи активности пользователей'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Удалить записи старше указанного количества дней (по умолчанию 30)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Показать, что будет удалено, без фактического удаления'
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Получаем записи для удаления
        old_activities = UserActivity.objects.filter(last_seen__lt=cutoff_date)
        count = old_activities.count()
        
        if count == 0:
            self.stdout.write(
                self.style.SUCCESS(f'Нет записей активности старше {days} дней')
            )
            return
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'Будет удалено {count} записей активности старше {days} дней'
                )
            )
            self.stdout.write(f'Дата отсечения: {cutoff_date}')
            
            # Показываем примеры записей
            sample_activities = old_activities[:5]
            self.stdout.write('\nПримеры записей для удаления:')
            for activity in sample_activities:
                self.stdout.write(
                    f'  - {activity.user.username}: {activity.last_seen}'
                )
            
            if count > 5:
                self.stdout.write(f'  ... и еще {count - 5} записей')
            
            return
        
        # Удаляем старые записи
        deleted_count = old_activities.delete()[0]
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Успешно удалено {deleted_count} записей активности старше {days} дней'
            )
        )
        
        # Показываем статистику
        total_activities = UserActivity.objects.count()
        self.stdout.write(f'Всего записей активности: {total_activities}')
        
        # Показываем самую старую запись
        oldest_activity = UserActivity.objects.order_by('last_seen').first()
        if oldest_activity:
            self.stdout.write(
                f'Самая старая запись: {oldest_activity.user.username} - {oldest_activity.last_seen}'
            ) 