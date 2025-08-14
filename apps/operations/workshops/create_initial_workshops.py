from django.core.management.base import BaseCommand
from apps.operations.workshops.models import Workshop

WORKSHOPS = [
    'Распиловка',
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

def create_workshops():
    for name in WORKSHOPS:
        Workshop.objects.get_or_create(name=name)
    print('Цеха успешно созданы (или уже существуют).')

if __name__ == '__main__':
    create_workshops() 