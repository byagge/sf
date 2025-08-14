from django.core.management.base import BaseCommand
from apps.employee_tasks.models import EmployeeTask
from apps.orders.models import OrderStage

class Command(BaseCommand):
    help = 'Удаляет EmployeeTask, у которых stage_id не существует в OrderStage.'

    def handle(self, *args, **options):
        valid_stage_ids = set(OrderStage.objects.values_list('id', flat=True))
        invalid_tasks = EmployeeTask.objects.exclude(stage_id__in=valid_stage_ids)
        count = invalid_tasks.count()
        invalid_tasks.delete()
        self.stdout.write(self.style.SUCCESS(f'Удалено {count} некорректных EmployeeTask')) 