from rest_framework import serializers
from apps.users.models import User
from django.utils import timezone

class WorkScheduleField(serializers.Field):
    def to_representation(self, value):
        # value: dict or None
        if not value:
            return {
                'monday': '', 'tuesday': '', 'wednesday': '', 'thursday': '', 'friday': '', 'saturday': '', 'sunday': ''
            }
        return value
    def to_internal_value(self, data):
        # data: dict
        return data or {
            'monday': '', 'tuesday': '', 'wednesday': '', 'thursday': '', 'friday': '', 'saturday': '', 'sunday': ''
        }

class EmployeeSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    workshop_name = serializers.CharField(source='workshop.name', read_only=True)
    
    # Для фронта:
    name = serializers.CharField(source='get_full_name', read_only=True)
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    position = serializers.CharField(source='role')
    status = serializers.SerializerMethodField()
    passportNumber = serializers.CharField(source='passport_number', required=False, allow_blank=True)
    taxId = serializers.CharField(source='inn', required=False, allow_blank=True)
    startDate = serializers.DateField(source='employment_date', required=False, allow_null=True)
    firedDate = serializers.DateField(source='fired_date', required=False, allow_null=True)
    contractNumber = serializers.CharField(source='contract_number', required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    
    # Статистика (из связанной модели)
    salary = serializers.SerializerMethodField()
    completed_works = serializers.SerializerMethodField()
    defects = serializers.SerializerMethodField()
    efficiency = serializers.SerializerMethodField()
    monthly_salary = serializers.SerializerMethodField()
    
    # Задачи (из связанной модели)
    tasks = serializers.SerializerMethodField()
    
    # Уведомления (из связанной модели)
    notifications = serializers.SerializerMethodField()
    
    # Документы (из связанной модели)
    documents = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'first_name', 'last_name', 'name', 'full_name', 'position', 'phone', 'email', 'status',
            'workshop', 'workshop_name', 'passportNumber', 'taxId', 'startDate', 'firedDate',
            'contractNumber', 'notes', 'role_display', 'is_active', 'role',
            'passport_number', 'inn', 'employment_date', 'fired_date', 'contract_number',
            # Статистика
            'salary', 'completed_works', 'defects', 'efficiency', 'monthly_salary',
            # Связанные данные
            'tasks', 'notifications', 'documents',
        ]

    def get_status(self, obj):
        return 'active' if obj.is_active else 'inactive'
    
    def get_salary(self, obj):
        """Получить оклад из статистики"""
        if hasattr(obj, 'statistics') and obj.statistics:
            return float(obj.statistics.salary) if obj.statistics.salary else 0
        return 0
    
    def get_completed_works(self, obj):
        """Получить количество выполненных работ"""
        if hasattr(obj, 'statistics') and obj.statistics:
            return obj.statistics.completed_works
        return 0
    
    def get_defects(self, obj):
        """Получить количество браков"""
        if hasattr(obj, 'statistics') and obj.statistics:
            return obj.statistics.defects
        return 0
    
    def get_efficiency(self, obj):
        """Получить эффективность"""
        if hasattr(obj, 'statistics') and obj.statistics:
            return obj.statistics.efficiency
        return 0
    
    def get_monthly_salary(self, obj):
        """Получить заработок за месяц"""
        if hasattr(obj, 'statistics') and obj.statistics:
            return float(obj.statistics.monthly_salary) if obj.statistics.monthly_salary else 0
        return 0
    
    def get_tasks(self, obj):
        """Получить задачи сотрудника"""
        tasks = obj.tasks.all()[:10]  # Ограничиваем до 10 последних задач
        return [
            {
                'id': task.id,
                'text': task.text,
                'completed': task.completed,
                'created_at': task.created_at.isoformat() if task.created_at else None,
                'completed_at': task.completed_at.isoformat() if task.completed_at else None
            }
            for task in tasks
        ]
    
    def get_notifications(self, obj):
        """Получить уведомления сотрудника"""
        notifications = obj.notifications.all()[:5]  # Ограничиваем до 5 последних уведомлений
        return [
            {
                'id': notification.id,
                'title': notification.title,
                'text': notification.text,
                'is_read': notification.is_read,
                'created_at': notification.created_at.isoformat() if notification.created_at else None
            }
            for notification in notifications
        ]
    
    def get_documents(self, obj):
        """Получить документы сотрудника"""
        documents = obj.documents.all()
        return [
            {
                'id': doc.id,
                'document_type': doc.document_type,
                'document_type_display': doc.get_document_type_display(),
                'status': doc.status,
                'status_display': doc.get_status_display(),
                'expiry_date': doc.expiry_date.isoformat() if doc.expiry_date else None,
                'uploaded_at': doc.uploaded_at.isoformat() if doc.uploaded_at else None
            }
            for doc in documents
        ]

    def create(self, validated_data):
        # Обработка вложенных полей
        validated_data['role'] = validated_data.pop('role', validated_data.get('position', 'worker'))
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data['role'] = validated_data.pop('role', validated_data.get('position', instance.role))
        return super().update(instance, validated_data) 