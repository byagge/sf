from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from .models import Workshop
from apps.users.models import User


@receiver(pre_save, sender=Workshop)
def update_manager_role(sender, instance, **kwargs):
    """
    Автоматически изменяет роль пользователя на 'master' при назначении руководителем цеха
    """
    try:
        # Получаем старый объект из базы данных
        if instance.pk:
            old_instance = Workshop.objects.get(pk=instance.pk)
            old_manager = old_instance.manager
        else:
            old_manager = None
        
        new_manager = instance.manager
        
        # Если руководитель изменился
        if old_manager != new_manager:
            # Если был старый руководитель, возвращаем ему роль 'worker'
            if old_manager and old_manager.role == User.Role.MASTER:
                # Проверяем, не является ли он руководителем других цехов
                other_workshops = Workshop.objects.filter(manager=old_manager).exclude(pk=instance.pk)
                if not other_workshops.exists():
                    old_manager.role = User.Role.WORKER
                    old_manager.save()
            
            # Если назначен новый руководитель, меняем его роль на 'master'
            if new_manager and new_manager.role != User.Role.MASTER:
                new_manager.role = User.Role.MASTER
                new_manager.save()
                
    except Workshop.DoesNotExist:
        # Если это новый объект, просто назначаем роль новому руководителю
        if instance.manager and instance.manager.role != User.Role.MASTER:
            instance.manager.role = User.Role.MASTER
            instance.manager.save()
    except Exception as e:
        # Логируем ошибку, но не прерываем сохранение
        print(f"Ошибка при обновлении роли руководителя: {e}")


@receiver(post_save, sender=Workshop)
def ensure_manager_role(sender, instance, created, **kwargs):
    """
    Дополнительная проверка после сохранения, чтобы убедиться, что роль установлена правильно
    """
    if instance.manager and instance.manager.role != User.Role.MASTER:
        instance.manager.role = User.Role.MASTER
        instance.manager.save() 