from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.orders.models import OrderStage
from apps.notifications.models import Notification


@receiver(post_save, sender=OrderStage)
def notify_masters_on_new_stage(sender, instance: OrderStage, created: bool, **kwargs):
	# Notify only when a new workshop stage is created and linked to a workshop
	if not created:
		return
	if instance.stage_type != 'workshop':
		return
	if not instance.workshop:
		return

	workshop = instance.workshop

	# Get all masters for the workshop (main + additional)
	try:
		masters = workshop.get_all_masters()
	except Exception:
		masters = []

	if not masters:
		return

	# Build notification content
	title = f"Новые заявки в цех {workshop.name}"
	order_name = getattr(instance.order, 'name', None) or f"#{getattr(instance.order, 'id', '')}".strip()
	message = (
		f"В цех {workshop.name} поступили новые заявки"
	)
	if order_name:
		message += f" по заказу {order_name}"
	message += "."

	# Create notifications for each master
	for master in masters:
		try:
			Notification.objects.create(
				user=master,
				title=title,
				message=message,
				notification_type='info',
			)
		except Exception:
			# Silently ignore failures to avoid breaking order flow
			continue 