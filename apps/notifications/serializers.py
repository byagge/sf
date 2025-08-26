from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
	Notification, NotificationType, NotificationTemplate, 
	NotificationGroup, NotificationPreference, NotificationLog
)
from django.utils import timezone

User = get_user_model()

# Local fallback choices to avoid relying on model constants
PRIORITY_CHOICES = [
	('low', 'Низкий'),
	('medium', 'Средний'),
	('high', 'Высокий'),
	('urgent', 'Срочно'),
]
STATUS_CHOICES = [
	('unread', 'Непрочитано'),
	('read', 'Прочитано'),
]


class UserSerializer(serializers.ModelSerializer):
	"""Сериализатор для пользователя"""
	full_name = serializers.SerializerMethodField()
	
	class Meta:
		model = User
		fields = ['id', 'username', 'email', 'first_name', 'last_name', 'full_name']
	
	def get_full_name(self, obj):
		return obj.get_full_name() or obj.username


class NotificationTypeSerializer(serializers.ModelSerializer):
	"""Сериализатор для типа уведомления"""
	
	class Meta:
		model = NotificationType
		fields = '__all__'


class NotificationSerializer(serializers.ModelSerializer):
	"""Сериализатор для уведомления (упрощён под текущую модель)"""
	user = UserSerializer(read_only=True)
	
	class Meta:
		model = Notification
		fields = [
			'id', 'title', 'message', 'notification_type',
			'user', 'is_read', 'created_at'
		]
		read_only_fields = ['id', 'created_at', 'user']


class NotificationUpdateSerializer(serializers.ModelSerializer):
	"""Сериализатор для обновления уведомления (только флаг прочитано)"""
	
	class Meta:
		model = Notification
		fields = ['is_read']


class NotificationTemplateSerializer(serializers.ModelSerializer):
	"""Сериализатор для шаблона уведомления"""
	notification_type = NotificationTypeSerializer(read_only=True)
	notification_type_id = serializers.IntegerField(write_only=True)
	
	class Meta:
		model = NotificationTemplate
		fields = [
			'id', 'name', 'notification_type', 'notification_type_id',
			'title_template', 'message_template', 'is_active',
			'created_at', 'updated_at'
		]
		read_only_fields = ['id', 'created_at', 'updated_at']


class NotificationGroupSerializer(serializers.ModelSerializer):
	"""Сериализатор для группы уведомлений"""
	recipients = UserSerializer(many=True, read_only=True)
	notification_type = NotificationTypeSerializer(read_only=True)
	notification_type_id = serializers.IntegerField(write_only=True)
	recipient_ids = serializers.ListField(
		child=serializers.IntegerField(),
		write_only=True,
		required=False
	)
	
	class Meta:
		model = NotificationGroup
		fields = [
			'id', 'name', 'description', 'recipients', 'notification_type',
			'notification_type_id', 'is_active', 'created_at', 'recipient_ids'
		]
		read_only_fields = ['id', 'created_at']
	
	def create(self, validated_data):
		recipient_ids = validated_data.pop('recipient_ids', [])
		notification_type_id = validated_data.pop('notification_type_id')
		
		# Получаем тип уведомления
		notification_type = NotificationType.objects.get(id=notification_type_id)
		
		# Создаем группу
		group = NotificationGroup.objects.create(
			notification_type=notification_type,
			**validated_data
		)
		
		# Добавляем получателей
		if recipient_ids:
			recipients = User.objects.filter(id__in=recipient_ids)
			group.recipients.set(recipients)
		
		return group


class NotificationPreferenceSerializer(serializers.ModelSerializer):
	"""Сериализатор для настроек уведомлений"""
	user = UserSerializer(read_only=True)
	
	class Meta:
		model = NotificationPreference
		fields = [
			'id', 'user', 'email_notifications', 'email_daily_digest',
			'email_weekly_digest', 'push_notifications', 'sms_notifications',
			'preferences_by_type', 'quiet_hours_start', 'quiet_hours_end',
			'created_at', 'updated_at'
		]
		read_only_fields = ['id', 'user', 'created_at', 'updated_at']


class NotificationLogSerializer(serializers.ModelSerializer):
	"""Сериализатор для лога уведомлений"""
	notification = NotificationSerializer(read_only=True)
	
	class Meta:
		model = NotificationLog
		fields = [
			'id', 'notification', 'sent_at', 'delivery_method',
			'delivery_status', 'error_message'
		]
		read_only_fields = ['id', 'sent_at']


class BulkNotificationSerializer(serializers.Serializer):
	"""Сериализатор для массовой отправки уведомлений (упрощён)"""
	title = serializers.CharField(max_length=200)
	message = serializers.CharField()
	notification_type_id = serializers.IntegerField(required=False)
	recipient_ids = serializers.ListField(
		child=serializers.IntegerField(),
		min_length=1
	)
	priority = serializers.ChoiceField(
		choices=PRIORITY_CHOICES,
		default='medium'
	)
	action_url = serializers.URLField(required=False, allow_blank=True)
	action_text = serializers.CharField(max_length=100, required=False, allow_blank=True)
	expires_at = serializers.DateTimeField(required=False, allow_null=True)
	metadata = serializers.JSONField(required=False, default=dict)


class NotificationStatsSerializer(serializers.Serializer):
	"""Сериализатор для статистики уведомлений"""
	total_notifications = serializers.IntegerField()
	unread_count = serializers.IntegerField()
	read_count = serializers.IntegerField()
	archived_count = serializers.IntegerField()
	notifications_by_type = serializers.DictField()
	notifications_by_priority = serializers.DictField()
	recent_notifications = NotificationSerializer(many=True)


class MarkAsReadSerializer(serializers.Serializer):
	"""Сериализатор для отметки уведомлений как прочитанных"""
	notification_ids = serializers.ListField(
		child=serializers.IntegerField(),
		min_length=1
	)
	mark_all = serializers.BooleanField(default=False)


class NotificationFilterSerializer(serializers.Serializer):
	"""Сериализатор для фильтрации уведомлений (упрощён)"""
	status = serializers.ChoiceField(
		choices=STATUS_CHOICES,
		required=False
	)
	priority = serializers.ChoiceField(
		choices=PRIORITY_CHOICES,
		required=False
	)
	notification_type_id = serializers.IntegerField(required=False)
	date_from = serializers.DateField(required=False)
	date_to = serializers.DateField(required=False)
	search = serializers.CharField(required=False)
	page = serializers.IntegerField(default=1, min_value=1)
	page_size = serializers.IntegerField(default=20, min_value=1, max_value=100) 