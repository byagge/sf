from django.core.management.base import BaseCommand
from apps.support.models import SupportCategory


class Command(BaseCommand):
    help = 'Настройка начальных категорий поддержки'

    def handle(self, *args, **options):
        categories = [
            {
                'name': 'Техническая поддержка',
                'description': 'Вопросы по работе с системой, ошибки, баги'
            },
            {
                'name': 'Обучение',
                'description': 'Вопросы по использованию функций системы'
            },
            {
                'name': 'Отчеты',
                'description': 'Помощь с формированием и анализом отчетов'
            },
            {
                'name': 'Интеграция',
                'description': 'Вопросы по интеграции с внешними системами'
            },
            {
                'name': 'Общие вопросы',
                'description': 'Общие вопросы по работе системы'
            }
        ]

        created_count = 0
        for category_data in categories:
            category, created = SupportCategory.objects.get_or_create(
                name=category_data['name'],
                defaults={'description': category_data['description']}
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Создана категория: {category.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Категория уже существует: {category.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'Настройка завершена. Создано категорий: {created_count}')
        ) 