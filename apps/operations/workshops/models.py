from django.db import models

class Workshop(models.Model):
    name = models.CharField('Название цеха', max_length=100)
    manager = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='operation_managed_workshops',
        limit_choices_to={'role': 'master'},
        verbose_name='Руководитель (мастер)'
    )
    description = models.TextField('Описание', blank=True)
    is_active = models.BooleanField('Активен', default=True)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)

    class Meta:
        verbose_name = 'Цех'
        verbose_name_plural = 'Цеха'

    def __str__(self):
        return self.name

    def set_manager(self, user):
        """
        Назначает пользователя руководителем цеха и автоматически изменяет его роль на 'master'
        """
        from apps.users.models import User
        
        # Если был предыдущий руководитель, возвращаем ему роль 'worker'
        if self.manager and self.manager != user:
            # Проверяем, не является ли он руководителем других цехов
            other_workshops = Workshop.objects.filter(manager=self.manager).exclude(pk=self.pk)
            if not other_workshops.exists():
                self.manager.role = User.Role.WORKER
                self.manager.save()
        
        # Назначаем нового руководителя
        self.manager = user
        
        # Изменяем роль нового руководителя на 'master'
        if user and user.role != User.Role.MASTER:
            user.role = User.Role.MASTER
            user.save()
        
        # Сохраняем цех
        self.save()
