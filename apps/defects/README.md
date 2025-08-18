# Система браков (Defects)

## Описание

Новая система браков обеспечивает контроль качества продукции с обязательным подтверждением мастером. Штрафы за брак начисляются только после проверки и подтверждения мастером, а не автоматически при создании брака.

## Основные принципы

1. **Сотрудник отмечает брак** в своей задаче (`EmployeeTask.defective_quantity`)
2. **Автоматически создается запись** в системе браков (`Defect`) со статусом "Ожидает подтверждения мастера"
3. **Мастер проверяет брак** и принимает решение:
   - Можно ли починить брак
   - Если нельзя починить - определяет тип брака (технический/ручной)
4. **Штраф начисляется только** для ручных браков после подтверждения мастером

## Модели

### Defect (Брак)

```python
class Defect(models.Model):
    # Связь с задачей сотрудника
    employee_task = models.ForeignKey('employee_tasks.EmployeeTask')
    
    # Основная информация
    product = models.ForeignKey(Product)
    user = models.ForeignKey(User)  # Сотрудник, создавший брак
    created_at = models.DateTimeField()
    
    # Статус и тип
    status = models.CharField(choices=DefectStatus.choices, default='pending')
    defect_type = models.CharField(choices=DefectType.choices, null=True)
    
    # Подтверждение мастером
    confirmed_by = models.ForeignKey(User, limit_choices_to={'role': 'master'})
    confirmed_at = models.DateTimeField()
    is_repairable = models.BooleanField()
    
    # Штрафы
    penalty_amount = models.DecimalField(default=0)
    penalty_applied = models.BooleanField(default=False)
```

### Статусы брака

- `pending` - Ожидает подтверждения мастера
- `confirmed` - Подтвержден мастером
- `repairable` - Можно починить
- `irreparable` - Нельзя починить
- `transferred` - Переведен в другой цех
- `repaired` - Починен
- `closed` - Закрыт

### Типы брака

- `technical` - Технический (штраф не списывается с сотрудника)
- `manual` - Ручной (штраф списывается с сотрудника)

## API Endpoints

### Получение списка браков
```
GET /defects/api/defects/
```

### Подтверждение брака мастером
```
POST /defects/api/defects/{id}/confirm/
{
    "is_repairable": true/false,
    "defect_type": "technical"/"manual",  // только если is_repairable=false
    "target_workshop_id": 123,  // опционально
    "comment": "Комментарий мастера"
}
```

### Отметка брака как починенного
```
POST /defects/api/defects/{id}/mark_repaired/
{
    "comment": "Комментарий по починке"
}
```

### Закрытие брака
```
POST /defects/api/defects/{id}/close/
```

### Статистика браков
```
GET /defects/api/stats/
```

## Логика работы

### 1. Создание брака
При изменении `defective_quantity` в `EmployeeTask` автоматически создаются записи в `Defect`:

```python
@receiver(pre_save, sender=EmployeeTask)
def create_defect_on_defective_change(sender, instance, **kwargs):
    if instance.defective_quantity > old_instance.defective_quantity:
        defect_quantity = instance.defective_quantity - old_instance.defective_quantity
        for _ in range(defect_quantity):
            Defect.objects.create(
                employee_task=instance,
                product=instance.stage.order_item.product,
                user=instance.employee,
                status='pending'
            )
```

### 2. Подтверждение мастером
Мастер проверяет брак и принимает решение:

```python
def confirm_defect(self, master, is_repairable, defect_type=None, target_workshop=None, comment=''):
    self.confirmed_by = master
    self.confirmed_at = timezone.now()
    self.is_repairable = is_repairable
    
    if is_repairable:
        self.status = 'repairable'
    else:
        self.status = 'irreparable'
        self.defect_type = defect_type
        if defect_type == 'manual':
            self._apply_penalty()  # Начисляем штраф
```

### 3. Начисление штрафа
Штраф начисляется только для ручных браков:

```python
def _apply_penalty(self):
    if self.defect_type == 'manual':
        service = Service.objects.filter(workshop=self.user.workshop, is_active=True).first()
        if service:
            self.penalty_amount = service.defect_penalty
            self.penalty_applied = True
            
            # Обновляем штраф в задаче сотрудника
            self.employee_task.penalties += self.penalty_amount
            self.employee_task.net_earnings = self.employee_task.earnings - self.employee_task.penalties
            self.employee_task.save()
```

## Изменения в EmployeeTask

### Убрано автоматическое начисление штрафов
В методе `calculate_earnings()` убрана строка:
```python
# Было:
self.penalties = Decimal(str(self.defective_quantity)) * self.service.defect_penalty

# Стало:
# Штрафы теперь начисляются только после подтверждения мастером
```

### Штрафы обновляются только при подтверждении брака
Штрафы в `EmployeeTask` обновляются только когда мастер подтверждает ручной брак.

## Миграции

Для применения изменений выполните:
```bash
python manage.py migrate defects
```

## Тестирование

Для тестирования новой системы используйте скрипт:
```bash
python test_new_defect_system.py
```

## Интерфейс

### Страница браков
- `/defects/` - Основная страница списка браков
- `/defects/mobile/` - Мобильная версия

### Модальные окна
1. **Подтверждение брака** - мастер подтверждает проверку
2. **Выбор типа брака** - для неисправимых браков
3. **Выбор цеха** - для перевода брака
4. **Отметка починки** - отметка брака как починенного

## Права доступа

- **Сотрудники** - видят только свои браки
- **Мастера** - видят браки своего цеха, могут подтверждать браки
- **Администраторы** - видят все браки, могут закрывать браки 