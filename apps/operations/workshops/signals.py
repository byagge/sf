from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from .models import Workshop, WorkshopMaster
from apps.users.models import User


@receiver(pre_save, sender=Workshop)
def update_manager_role(sender, instance, **kwargs):
    """
    Автоматически изменяет роль пользователя на 'master' при назначении главным руководителем цеха
    """
    try:
        # Получаем старый объект из базы данных
        if instance.pk:
            old_instance = Workshop.objects.get(pk=instance.pk)
            old_manager = old_instance.manager
        else:
            old_manager = None
        
        new_manager = instance.manager
        
        # Если главный руководитель изменился
        if old_manager != new_manager:
            # Если был старый главный руководитель, проверяем, нужно ли вернуть ему роль 'worker'
            if old_manager and old_manager.role == User.Role.MASTER:
                # Проверяем, не является ли он руководителем других цехов или дополнительным мастером
                other_workshops = Workshop.objects.filter(manager=old_manager).exclude(pk=instance.pk)
                other_workshop_masters = WorkshopMaster.objects.filter(master=old_manager, is_active=True)
                if not other_workshops.exists() and not other_workshop_masters.exists():
                    old_manager.role = User.Role.WORKER
                    old_manager.save()
            
            # Если назначен новый главный руководитель, меняем его роль на 'master'
            if new_manager and new_manager.role != User.Role.MASTER:
                new_manager.role = User.Role.MASTER
                new_manager.save()
                
    except Workshop.DoesNotExist:
        # Если это новый объект, просто назначаем роль новому главному руководителю
        if instance.manager and instance.manager.role != User.Role.MASTER:
            instance.manager.role = User.Role.MASTER
            instance.manager.save()
    except Exception as e:
        # Логируем ошибку, но не прерываем сохранение
        print(f"Ошибка при обновлении роли главного руководителя: {e}")


@receiver(post_save, sender=Workshop)
def ensure_manager_role(sender, instance, created, **kwargs):
    """
    Дополнительная проверка после сохранения, чтобы убедиться, что роль установлена правильно
    """
    if instance.manager and instance.manager.role != User.Role.MASTER:
        instance.manager.role = User.Role.MASTER
        instance.manager.save()


@receiver(post_save, sender=WorkshopMaster)
def update_workshop_master_role(sender, instance, created, **kwargs):
    """
    Автоматически изменяет роль пользователя на 'master' при назначении дополнительным мастером цеха
    """
    if created and instance.is_active:
        if instance.master.role != User.Role.MASTER:
            instance.master.role = User.Role.MASTER
            instance.master.save()


@receiver(post_save, sender=WorkshopMaster)
def handle_workshop_master_status_change(sender, instance, **kwargs):
    """
    Обрабатывает изменение статуса дополнительного мастера
    """
    if not instance.is_active:
        # Если мастер деактивирован, проверяем, нужно ли вернуть ему роль 'worker'
        other_workshops = Workshop.objects.filter(manager=instance.master)
        other_workshop_masters = WorkshopMaster.objects.filter(master=instance.master, is_active=True)
        
        if not other_workshops.exists() and not other_workshop_masters.exists():
            instance.master.role = User.Role.WORKER
            instance.master.save()


@receiver(post_delete, sender=WorkshopMaster)
def handle_workshop_master_deletion(sender, instance, **kwargs):
    """
    Обрабатывает удаление дополнительного мастера
    """
    # Проверяем, не является ли пользователь мастером других цехов
    other_workshops = Workshop.objects.filter(manager=instance.master)
    other_workshop_masters = WorkshopMaster.objects.filter(master=instance.master, is_active=True)
    
    if not other_workshops.exists() and not other_workshop_masters.exists():
        instance.master.role = User.Role.WORKER
        instance.master.save() 