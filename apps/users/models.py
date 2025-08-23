from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.cache import cache
from django.utils import timezone
from django.db.models import Q, Count, Avg
from cacheops import cached_as, cached
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
        verbose_name='Роль',
        db_index=True  # Добавляем индекс для быстрого поиска по роли
    )
    phone = models.CharField(
        max_length=20, 
        verbose_name='Телефон', 
        blank=True,
        db_index=True  # Индекс для поиска по телефону
    )
    email = models.EmailField(
        verbose_name='Email', 
        blank=True,
        db_index=True  # Индекс для поиска по email
    )
    workshop = models.ForeignKey(
        'operations_workshops.Workshop',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        verbose_name='Цех',
        db_index=True  # Индекс для внешнего ключа
    )
    passport_number = models.CharField('Паспорт', max_length=30, blank=True)
    inn = models.CharField('ИНН', max_length=20, blank=True, db_index=True)
    employment_date = models.DateField(
        'Дата приема на работу', 
        null=True, 
        blank=True,
        db_index=True  # Индекс для фильтрации по дате приема
    )
    fired_date = models.DateField('Дата увольнения', null=True, blank=True)
    contract_number = models.CharField(
        'Номер трудового договора', 
        max_length=50, 
        blank=True,
        db_index=True
    )
    notes = models.TextField('Примечания', blank=True)
    
    # Системные поля
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name='Дата создания',
        db_index=True
    )
    updated_at = models.DateTimeField(
        auto_now=True, 
        verbose_name='Дата обновления'
    )
    
    # Дополнительные поля для оптимизации
    is_active_employee = models.BooleanField(
        'Активный сотрудник',
        default=True,
        db_index=True,
        help_text='Указывает, является ли сотрудник активным'
    )
    last_activity = models.DateTimeField(
        'Последняя активность',
        null=True,
        blank=True,
        db_index=True
    )

    class Meta:
        db_table = 'users_user'
        indexes = [
            models.Index(fields=['role', 'is_active_employee']),
            models.Index(fields=['workshop', 'is_active_employee']),
            models.Index(fields=['employment_date', 'is_active_employee']),
            models.Index(fields=['created_at', 'role']),
            models.Index(fields=['last_activity']),
        ]
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

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
        
        # Обновляем статус активного сотрудника
        if self.fired_date and self.fired_date <= timezone.now().date():
            self.is_active_employee = False
        
        super().save(*args, **kwargs)
        
        # Инвалидируем кэш
        self._invalidate_cache()

    def _invalidate_cache(self):
        """Инвалидирует кэш для пользователя"""
        cache_keys = [
            f'user_stats_{self.id}',
            f'user_tasks_{self.id}',
            f'user_notifications_{self.id}',
            f'workshop_users_{self.workshop_id}' if self.workshop_id else None,
            f'role_users_{self.role}',
        ]
        
        for key in cache_keys:
            if key:
                cache.delete(key)

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
    
    @cached(timeout=300)  # Кэшируем на 5 минут
    def get_statistics(self):
        """
        Возвращает статистику сотрудника с кэшированием
        """
        from apps.employee_tasks.models import EmployeeTask
        from apps.attendance.models import Attendance
        
        # Получаем статистику из кэша или вычисляем
        cache_key = f'user_stats_{self.id}'
        stats = cache.get(cache_key)
        
        if stats is None:
            # Вычисляем статистику
            tasks = EmployeeTask.objects.filter(employee=self)
            attendance = Attendance.objects.filter(employee=self)
            
            stats = {
                'total_tasks': tasks.count(),
                'completed_tasks': tasks.filter(status='completed').count(),
                'pending_tasks': tasks.filter(status='pending').count(),
                'attendance_days': attendance.count(),
                'last_activity': self.last_activity,
                'employment_duration': (timezone.now().date() - self.employment_date).days if self.employment_date else 0,
            }
            
            # Кэшируем на 5 минут
            cache.set(cache_key, stats, 300)
        
        return stats
    
    @cached(timeout=60)  # Кэшируем на 1 минуту
    def get_tasks(self):
        """
        Возвращает задачи сотрудника с кэшированием
        """
        from apps.employee_tasks.models import EmployeeTask
        
        cache_key = f'user_tasks_{self.id}'
        tasks = cache.get(cache_key)
        
        if tasks is None:
            tasks = list(EmployeeTask.objects.filter(employee=self).select_related('task_type'))
            cache.set(cache_key, tasks, 60)
        
        return tasks
    
    @cached(timeout=30)  # Кэшируем на 30 секунд
    def get_notifications(self):
        """
        Возвращает уведомления сотрудника с кэшированием
        """
        from apps.notifications.models import Notification
        
        cache_key = f'user_notifications_{self.id}'
        notifications = cache.get(cache_key)
        
        if notifications is None:
            notifications = list(Notification.objects.filter(user=self, is_read=False))
            cache.set(cache_key, notifications, 30)
        
        return notifications
    
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

    def update_last_activity(self):
        """Обновляет время последней активности"""
        self.last_activity = timezone.now()
        self.save(update_fields=['last_activity'])

    @classmethod
    @cached(timeout=600)  # Кэшируем на 10 минут
    def get_active_employees(cls):
        """Возвращает всех активных сотрудников с кэшированием"""
        return list(cls.objects.filter(is_active_employee=True).select_related('workshop'))

    @classmethod
    @cached(timeout=600)
    def get_employees_by_role(cls, role):
        """Возвращает сотрудников по роли с кэшированием"""
        cache_key = f'role_users_{role}'
        users = cache.get(cache_key)
        
        if users is None:
            users = list(cls.objects.filter(role=role, is_active_employee=True))
            cache.set(cache_key, users, 600)
        
        return users

    @classmethod
    @cached(timeout=300)
    def get_workshop_employees(cls, workshop_id):
        """Возвращает сотрудников цеха с кэшированием"""
        cache_key = f'workshop_users_{workshop_id}'
        users = cache.get(cache_key)
        
        if users is None:
            users = list(cls.objects.filter(workshop_id=workshop_id, is_active_employee=True))
            cache.set(cache_key, users, 300)
        
        return users

    @classmethod
    def get_employee_statistics(cls):
        """Возвращает общую статистику по сотрудникам"""
        cache_key = 'employee_statistics'
        stats = cache.get(cache_key)
        
        if stats is None:
            stats = {
                'total_employees': cls.objects.filter(is_active_employee=True).count(),
                'by_role': dict(cls.objects.filter(is_active_employee=True)
                               .values('role')
                               .annotate(count=Count('id'))
                               .values_list('role', 'count')),
                'by_workshop': dict(cls.objects.filter(is_active_employee=True)
                                   .values('workshop__name')
                                   .annotate(count=Count('id'))
                                   .values_list('workshop__name', 'count')),
            }
            cache.set(cache_key, stats, 600)  # Кэшируем на 10 минут
        
        return stats
