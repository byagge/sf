from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

User = get_user_model()

class UserActivity(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    last_seen = models.DateTimeField(auto_now=True)
    is_online = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Активность пользователя'
        verbose_name_plural = 'Активность пользователей'
        ordering = ['-last_seen']
    
    def __str__(self):
        return f"{self.user.username} - {'Онлайн' if self.is_online else 'Офлайн'}"
    
    @classmethod
    def get_online_users(cls):
        """Получить всех пользователей, которые были активны в последние 15 минут"""
        threshold = timezone.now() - timedelta(minutes=15)
        return cls.objects.filter(last_seen__gte=threshold, is_online=True)
    
    @classmethod
    def update_user_activity(cls, user):
        """Обновить активность пользователя"""
        activity, created = cls.objects.get_or_create(user=user)
        activity.last_seen = timezone.now()
        activity.is_online = True
        activity.save()
        return activity
