from django.core.management.base import BaseCommand
from apps.employee_tasks.models import EmployeeTask
from decimal import Decimal

class Command(BaseCommand):
    help = 'Пересчитывает заработок для всех задач сотрудников'

    def handle(self, *args, **options):
        self.stdout.write('Начинаю пересчет заработка...')
        
        tasks = EmployeeTask.objects.all()
        updated_count = 0
        
        for task in tasks:
            try:
                # Сохраняем старые значения для сравнения
                old_earnings = task.earnings
                old_penalties = task.penalties
                old_net_earnings = task.net_earnings
                
                # Пересчитываем заработок
                task.calculate_earnings()
                
                # Проверяем, изменились ли значения
                if (task.earnings != old_earnings or 
                    task.penalties != old_penalties or 
                    task.net_earnings != old_net_earnings):
                    
                    # Сохраняем в базе
                    EmployeeTask.objects.filter(pk=task.pk).update(
                        earnings=task.earnings,
                        penalties=task.penalties,
                        net_earnings=task.net_earnings
                    )
                    updated_count += 1
                    
                    self.stdout.write(
                        f'Задача {task.id}: {task.employee.username} - '
                        f'Заработок: {old_earnings} → {task.earnings}, '
                        f'Штрафы: {old_penalties} → {task.penalties}, '
                        f'Чистый: {old_net_earnings} → {task.net_earnings}'
                    )
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'Ошибка при обработке задачи {task.id}: {e}'
                    )
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Пересчет завершен. Обновлено задач: {updated_count}'
            )
        ) 