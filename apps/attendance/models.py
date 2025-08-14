from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import time

# Create your models here.

class AttendanceRecord(models.Model):
    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='attendance_records',
        verbose_name='Сотрудник'
    )
    date = models.DateField(
        auto_now_add=True,
        verbose_name='Дата'
    )
    check_in = models.DateTimeField(
        verbose_name='Время прихода'
    )
    check_out = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Время ухода'
    )
    note = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Комментарий'
    )
    penalty_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        verbose_name='Сумма штрафа'
    )
    is_late = models.BooleanField(
        default=False,
        verbose_name='Опоздание'
    )

    class Meta:
        verbose_name = 'Запись о приходе'
        verbose_name_plural = 'Записи о приходах'
        unique_together = ('employee', 'date')
        ordering = ['-date', '-check_in']

    def __str__(self):
        return f"{self.employee.get_full_name()} — {self.date} ({self.check_in:%H:%M})"

    def calculate_penalty(self):
        """Рассчитывает штраф за опоздание после 9:00 по местному времени"""
        # Время начала рабочего дня
        work_start_time = time(9, 0)
        
        # Конвертируем UTC время в местное время
        local_check_in = timezone.localtime(self.check_in)
        check_in_time = local_check_in.time()
        
        if check_in_time > work_start_time:
            self.is_late = True
            # Штраф 500 сомов за опоздание (можно настроить)
            self.penalty_amount = 500.00
        else:
            self.is_late = False
            self.penalty_amount = 0.00
        
        return self.penalty_amount

    def get_late_status(self):
        """Возвращает статус опоздания без изменения модели"""
        work_start_time = time(9, 0)
        local_check_in = timezone.localtime(self.check_in)
        check_in_time = local_check_in.time()
        return check_in_time > work_start_time

    def recalculate_penalty(self):
        """Принудительно пересчитывает штраф (для существующих записей)"""
        old_penalty = self.penalty_amount
        old_is_late = self.is_late
        
        self.calculate_penalty()
        
        # Возвращаем True если что-то изменилось
        return old_penalty != self.penalty_amount or old_is_late != self.is_late

    def save(self, *args, **kwargs):
        # Автоматически рассчитываем штраф при сохранении
        print(f"DEBUG: Сохранение записи для {self.employee.get_full_name()}")
        print(f"DEBUG: UTC время прихода: {self.check_in}")
        
        # Показываем местное время
        local_time = timezone.localtime(self.check_in)
        print(f"DEBUG: Местное время прихода: {local_time}")
        print(f"DEBUG: До расчета - is_late: {self.is_late}, penalty: {self.penalty_amount}")
        
        self.calculate_penalty()
        
        print(f"DEBUG: После расчета - is_late: {self.is_late}, penalty: {self.penalty_amount}")
        
        super().save(*args, **kwargs)
