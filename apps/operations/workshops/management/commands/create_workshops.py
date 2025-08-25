from django.core.management.base import BaseCommand
from apps.operations.workshops.models import Workshop

class Command(BaseCommand):
    help = 'Создает начальные цеха в системе'

    def handle(self, *args, **options):
        WORKSHOPS = [
            'Распиловка',
            'Распил стекла',
            'Обработка на станках с ЧПУ',
            'Заготовительные работы',
            'Прессовое отделение',
            'Облицовка кромок',
            'Шлифовка (аппаратная)',
            'Шлифовка (сухая)',
            'Грунтование',
            'Шлифовка (белая)',
            'Окрасочное отделение',
            'Упаковка готовой продукции',
        ]

        created_count = 0
        for name in WORKSHOPS:
            workshop, created = Workshop.objects.get_or_create(
                name=name,
                defaults={
                    'description': f'Цех {name}',
                    'is_active': True
                }
            )
            if created:
                created_count += 1
                self.stdout.write(f'Создан цех: {name}')
            else:
                self.stdout.write(f'Цех уже существует: {name}')

        self.stdout.write(
            self.style.SUCCESS(f'Успешно создано {created_count} новых цехов из {len(WORKSHOPS)}')
        ) 