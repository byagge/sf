from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import UserActivity

User = get_user_model()

@receiver(post_save, sender=User)
def create_user_activity(sender, instance, created, **kwargs):
    """Создает запись активности при создании нового пользователя"""
    if created:
        UserActivity.objects.create(
            user=instance,
            last_seen=timezone.now(),
            is_online=True
        )

@receiver(post_save, sender=User)
def update_user_activity_on_save(sender, instance, **kwargs):
    """Обновляет активность пользователя при сохранении"""
    if not kwargs.get('created', False):  # Только для существующих пользователей
        try:
            activity = UserActivity.objects.get(user=instance)
            activity.last_seen = timezone.now()
            activity.save(update_fields=['last_seen'])
        except UserActivity.DoesNotExist:
            # Если записи нет, создаем новую
            UserActivity.objects.create(
                user=instance,
                last_seen=timezone.now(),
                is_online=True
            ) 