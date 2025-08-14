from django.contrib.auth.models import AbstractUser
from django.db import models
import re

class User(AbstractUser):
    class Role(models.TextChoices):
        FOUNDER = 'founder', 'Учредитель'
        DIRECTOR = 'director', 'Директор'
        ADMIN = 'admin', 'Администратор'
        ACCOUNTANT = 'accountant', 'Бухгалтер'
        MASTER = 'master', 'Мастер (руководитель цеха)'
        WORKER = 'worker', 'Рабочий'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.WORKER,
        verbose_name='Роль'
    )
    phone = models.CharField(max_length=20, verbose_name='Телефон', blank=True)
    email = models.EmailField(verbose_name='Email', blank=True)
    workshop = models.ForeignKey(
        'operations_workshops.Workshop',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        verbose_name='Цех'
    )
    passport_number = models.CharField('Паспорт', max_length=30, blank=True)
    inn = models.CharField('ИНН', max_length=20, blank=True)
    employment_date = models.DateField('Дата приема на работу', null=True, blank=True)
    fired_date = models.DateField('Дата увольнения', null=True, blank=True)
    contract_number = models.CharField('Номер трудового договора', max_length=50, blank=True)
    notes = models.TextField('Примечания', blank=True)
    
    # Системные поля
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True, 
        verbose_name='Дата обновления'
    )

    def __str__(self):
        return f"{self.get_full_name()} ({self.get_role_display()})"

    def get_full_name(self):
        """Возвращает полное имя (ФИО)"""
        if self.first_name and self.last_name:
            return f"{self.last_name} {self.first_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        else:
            return self.username

    def generate_username(self):
        """Генерирует username из имени и фамилии"""
        if self.first_name and self.last_name:
            # Создаем username из фамилии и имени (например: ИвановИван)
            base_username = f"{self.last_name}{self.first_name}"
            # Убираем пробелы и приводим к нижнему регистру
            username = re.sub(r'\s+', '', base_username).lower()
            # Заменяем кириллицу на латиницу
            cyrillic_to_latin = {
                'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'e',
                'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
                'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
                'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
                'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya'
            }
            for cyr, lat in cyrillic_to_latin.items():
                username = username.replace(cyr, lat)
            
            # Проверяем уникальность
            original_username = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{original_username}{counter}"
                counter += 1
            
            return username
        else:
            # Если нет имени/фамилии, используем email или генерируем случайный
            if self.email:
                return self.email.split('@')[0]
            else:
                return f"user{User.objects.count() + 1}"

    def save(self, *args, **kwargs):
        """Автоматически генерируем username при сохранении"""
        if not self.username:
            self.username = self.generate_username()
        super().save(*args, **kwargs)

    def is_workshop_manager(self):
        """
        Проверяет, является ли пользователь руководителем какого-либо цеха
        """
        return self.operation_managed_workshops.exists()

    def get_managed_workshops(self):
        """
        Возвращает список цехов, которыми управляет пользователь
        """
        return self.operation_managed_workshops.all()

    def can_be_workshop_manager(self):
        """
        Проверяет, может ли пользователь быть назначен руководителем цеха
        """
        return self.role in [self.Role.WORKER, self.Role.MASTER]
    
    def get_statistics(self):
        """
        Возвращает статистику сотрудника
        """
        return getattr(self, 'statistics', None)
    
    def get_tasks(self):
        """
        Возвращает задачи сотрудника
        """
        return self.tasks.all()
    
    def get_notifications(self):
        """
        Возвращает уведомления сотрудника
        """
        return self.notifications.all()
    
    def get_documents(self):
        """
        Возвращает документы сотрудника
        """
        return self.documents.all()
    
    def get_contact_info(self):
        """
        Возвращает контактную информацию сотрудника
        """
        return getattr(self, 'contact_info', None)
    
    def get_medical_info(self):
        """
        Возвращает медицинскую информацию сотрудника
        """
        return getattr(self, 'medical_info', None)
