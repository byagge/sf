from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.online.models import UserActivity

User = get_user_model()

class Command(BaseCommand):
    help = 'Инициализирует записи активности для существующих пользователей'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Принудительно обновить существующие записи'
        )
        parser.add_argument(
            '--users',
            type=str,
            help='Список пользователей через запятую (по умолчанию все)'
        )

    def handle(self, *args, **options):
        force = options['force']
        users_filter = options['users']
        
        if users_filter:
            usernames = [u.strip() for u in users_filter.split(',')]
            users = User.objects.filter(username__in=usernames)
            self.stdout.write(f'Обрабатываем {users.count()} указанных пользователей')
        else:
            users = User.objects.all()
            self.stdout.write(f'Обрабатываем всех пользователей ({users.count()})')
        
        created_count = 0
        updated_count = 0
        
        for user in users:
            try:
                activity, created = UserActivity.objects.get_or_create(
                    user=user,
                    defaults={
                        'last_seen': timezone.now(),
                        'is_online': True
                    }
                )
                
                if created:
                    created_count += 1
                    self.stdout.write(f'  Создана запись для {user.username}')
                elif force:
                    activity.last_seen = timezone.now()
                    activity.is_online = True
                    activity.save()
                    updated_count += 1
                    self.stdout.write(f'  Обновлена запись для {user.username}')
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Ошибка при обработке {user.username}: {e}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nИнициализация завершена:\n'
                f'  Создано записей: {created_count}\n'
                f'  Обновлено записей: {updated_count}\n'
                f'  Всего записей активности: {UserActivity.objects.count()}'
            )
        ) 