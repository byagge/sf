from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Order, OrderItem, OrderStage, OrderDefect
from .serializers import OrderSerializer, OrderItemSerializer, OrderStageConfirmSerializer, OrderStageSerializer
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from django.shortcuts import get_object_or_404
from django.db.models import Sum, Count, F
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from apps.employee_tasks.models import EmployeeTask
from apps.employees.models import User

# Create your views here.

class OrderViewSet(viewsets.ModelViewSet):
	queryset = Order.objects.select_related('client', 'workshop', 'product').prefetch_related('items__product', 'stages__workshop', 'order_defects__workshop').all().order_by('-created_at')
	serializer_class = OrderSerializer
	permission_classes = [permissions.IsAuthenticated]
	
	@action(detail=False, methods=['get'])
	def by_workshop(self, request):
		"""Получает заказы с разделением по цехам"""
		workshop_id = request.query_params.get('workshop_id')
		
		if workshop_id:
			# Фильтруем заказы по конкретному цеху
			queryset = Order.objects.filter(
				stages__workshop_id=workshop_id,
				stages__status__in=['in_progress', 'partial']
			).distinct().order_by('-created_at')
		else:
			# Получаем все заказы с группировкой по цехам
			queryset = Order.objects.filter(
				stages__status__in=['in_progress', 'partial']
			).distinct().order_by('-created_at')
		
		# Добавляем информацию о разделении по цехам
		orders_data = []
		for order in queryset:
			order_data = OrderSerializer(order).data
			
			# Добавляем информацию о цехах
			workshops_info = {}
			for stage in order.stages.filter(status__in=['in_progress', 'partial']):
				workshop_name = stage.workshop.name if stage.workshop else 'Не указан'
				workshop_type = 'Стеклянные товары' if stage.parallel_group == 1 else 'Обычные товары'
				
				if workshop_name not in workshops_info:
					workshops_info[workshop_name] = {
						'type': workshop_type,
						'quantity': 0,
						'operation': stage.operation
					}
				workshops_info[workshop_name]['quantity'] += stage.plan_quantity
			
			order_data['workshops_info'] = workshops_info
			order_data['has_glass_items'] = order.has_glass_items
			order_data['has_regular_items'] = order.regular_items
			
			orders_data.append(order_data)
		
		return Response(orders_data)
	
	def update(self, request, *args, **kwargs):
		instance = self.get_object()
		data = request.data.copy()
		
		# Обрабатываем позиции заказа отдельно
		items_data = data.pop('items_data', None)
		
		# Обновляем основные поля заказа
		serializer = self.get_serializer(instance, data=data, partial=True)
		serializer.is_valid(raise_exception=True)
		self.perform_update(serializer)
		
		# Если переданы новые позиции, обновляем их
		if items_data is not None:
			# Удаляем старые позиции
			instance.items.all().delete()
			
			# Создаем новые позиции
			for item_data in items_data:
				product_id = item_data.get('product_id')
				quantity = item_data.get('quantity', 1)
				size = item_data.get('size', '')
				color = item_data.get('color', '')
				glass_type = item_data.get('glass_type', '')
				paint_type = item_data.get('paint_type', '')
				paint_color = item_data.get('paint_color', '')
				cnc_specs = item_data.get('cnc_specs', '')
				cutting_specs = item_data.get('cutting_specs', '')
				packaging_notes = item_data.get('packaging_notes', '')
				
				# Проверяем что product_id существует и валиден
				if not product_id:
					continue
					
				from apps.products.models import Product
				try:
					product = Product.objects.get(pk=product_id)
				except Product.DoesNotExist:
					continue  # Пропускаем несуществующие товары
				
				OrderItem.objects.create(
					order=instance,
					product=product,
					quantity=quantity,
					size=size,
					color=color,
					glass_type=glass_type,
					paint_type=paint_type,
					paint_color=paint_color,
					cnc_specs=cnc_specs,
					cutting_specs=cutting_specs,
					packaging_notes=packaging_notes
				)
			
			# Удаляем старые этапы и создаем новые
			instance.stages.all().delete()
			from .models import create_order_stages
			try:
				create_order_stages(instance)
			except Exception as e:
				print(f"Warning: Error creating order stages: {e}")
				# Продолжаем выполнение, этапы не критичны для обновления заказа
		
		# Возвращаем обновленный заказ
		return Response(OrderSerializer(instance).data)

class OrderCreateAPIView(APIView):
	permission_classes = [permissions.IsAuthenticated]
	@method_decorator(csrf_exempt)
	def post(self, request):
		try:
			data = request.data
			name = data.get('name')
			client_id = data.get('client_id')
			items_data = data.get('items_data', [])
			
			if not name or not client_id or not items_data:
				return Response({
					'error': 'Необходимо указать название заказа, клиента и товары'
				}, status=status.HTTP_400_BAD_REQUEST)
			
			from apps.clients.models import Client
			client = get_object_or_404(Client, pk=client_id)
			
			# Создаем заказ
			order = Order.objects.create(
				name=name,
				client=client,
				status='production'
			)
			
			# Создаем позиции заказа
			created_items = []
			for item_data in items_data:
				product_id = item_data.get('product_id')
				quantity = item_data.get('quantity', 1)
				size = item_data.get('size', '')
				color = item_data.get('color', '')
				glass_type = item_data.get('glass_type', '')
				paint_type = item_data.get('paint_type', '')
				paint_color = item_data.get('paint_color', '')
				cnc_specs = item_data.get('cnc_specs', '')
				cutting_specs = item_data.get('cutting_specs', '')
				packaging_notes = item_data.get('packaging_notes', '')
				
				from apps.products.models import Product
				product = get_object_or_404(Product, pk=product_id)
				
				item = OrderItem.objects.create(
					order=order,
					product=product,
					quantity=quantity,
					size=size,
					color=color,
					glass_type=glass_type,
					paint_type=paint_type,
					paint_color=paint_color,
					cnc_specs=cnc_specs,
					cutting_specs=cutting_specs,
					packaging_notes=packaging_notes
				)
				created_items.append(item)
			
			# Автоматически создаем этапы заказа после создания всех позиций
			from .models import create_order_stages
			create_order_stages(order)
			
			# Возвращаем созданный заказ с полной информацией
			return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)
			
		except Exception as e:
			print('ORDER CREATE ERROR:', str(e))
			return Response({
				'error': f'Ошибка создания заказа: {str(e)}'
			}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class OrderPageView(View):
	def get(self, request):
		user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
		is_mobile = any(m in user_agent for m in ['android', 'iphone', 'ipad', 'mobile'])
		template = 'orders_mobile.html' if is_mobile else 'orders.html'
		show_create = request.GET.get('create') == 'True' or request.GET.get('create') == 'true' or request.GET.get('create') == '1'
		
		# Получаем статистику по заказам с разделением на стеклянные и обычные
		from apps.orders.models import Order
		from apps.operations.workshops.models import Workshop
		
		# Статистика по цехам
		workshops_stats = {}
		try:
			workshop_1 = Workshop.objects.get(pk=1)  # Обычные товары
			workshop_2 = Workshop.objects.get(pk=2)  # Стеклянные товары
			
			# Заказы в цехе 1 (обычные товары)
			regular_orders = Order.objects.filter(
				stages__workshop=workshop_1,
				stages__status__in=['in_progress', 'partial']
		 ).distinct().count()
			
			# Заказы в цехе 2 (стеклянные товары)
			glass_orders = Order.objects.filter(
				stages__workshop=workshop_2,
				stages__status__in=['in_progress', 'partial']
		 ).distinct().count()
			
			workshops_stats = {
				'workshop_1': {
					'name': workshop_1.name,
					'orders_count': regular_orders,
					'type': 'Обычные товары'
				},
				'workshop_2': {
					'name': workshop_2.name,
					'orders_count': glass_orders,
					'type': 'Стеклянные товары'
				}
			}
		except Workshop.DoesNotExist:
			workshops_stats = {}
		
		context = {
			'show_create': show_create,
			'workshops_stats': workshops_stats
		}
		return render(request, template, context)

class OrderStageConfirmAPIView(APIView):
	permission_classes = [permissions.IsAuthenticated]
	def patch(self, request, stage_id):
		stage = get_object_or_404(OrderStage, pk=stage_id)
		serializer = OrderStageConfirmSerializer(data=request.data)
		if serializer.is_valid():
			completed_qty = serializer.validated_data['completed_quantity']
			stage.confirm_stage(completed_qty)
			return Response({'status': 'ok', 'stage': stage.id, 'completed_quantity': completed_qty})
		return Response(serializer.errors, status=400)

class OrderStageTransferAPIView(APIView):
	permission_classes = [permissions.IsAuthenticated]
	def post(self, request, stage_id):
		stage = get_object_or_404(OrderStage, pk=stage_id)
		# Поддержка явного выбора цеха и количества, без жёсткого workflow
		target_workshop_id = request.data.get('target_workshop_id')
		completed_qty = request.data.get('completed_quantity')
		try:
			completed_qty = int(completed_qty) if completed_qty is not None else stage.plan_quantity
		except (TypeError, ValueError):
			completed_qty = stage.plan_quantity
		if completed_qty < 0:
			completed_qty = 0
		if completed_qty > stage.plan_quantity:
			completed_qty = stage.plan_quantity
		
		# Ограничения и логика для стеклянных изделий: только цеха 2 и 12; при переводе в 12 — агрегируем
		is_glass = bool(getattr(getattr(getattr(stage, 'order_item', None), 'product', None), 'is_glass', False))
		current_workshop_id = getattr(getattr(stage, 'workshop', None), 'id', None)
		
		if target_workshop_id:
			try:
				target_workshop_id = int(target_workshop_id)
			except (TypeError, ValueError):
				return Response({'error': 'target_workshop_id must be an integer'}, status=400)
			
			if is_glass:
				# Допускаем только перемещения между цехами 2 и 12
				if current_workshop_id not in (2, 12):
					return Response({'error': 'Glass items may only be processed in workshops 2 and 12'}, status=400)
				if target_workshop_id not in (2, 12):
					return Response({'error': 'Glass items can only be transferred to workshop 2 or 12'}, status=400)
				
				# Завершаем текущий этап на указанное количество (частично или полностью)
				stage.confirm_stage(completed_qty)
				from apps.operations.workshops.models import Workshop
				workshop = get_object_or_404(Workshop, pk=target_workshop_id)
				
				# Если переводим в 12 — агрегируем по заявке (order_item=NULL) в цехе 12
				if target_workshop_id == 12:
					# Ищем существующий агрегирующий этап по заказу без привязки к позиции в 12 цехе
					aggregate_stage = OrderStage.objects.filter(
						order=stage.order,
						order_item__isnull=True,
						workshop_id=12,
						stage_type='workshop',
						parallel_group=stage.parallel_group,
					).order_by('sequence').first()
					if aggregate_stage:
						aggregate_stage.plan_quantity += completed_qty
						aggregate_stage.status = 'in_progress'
						aggregate_stage.save(update_fields=['plan_quantity', 'status'])
					else:
						# Создаем новый агрегирующий этап
						OrderStage.objects.create(
							order=stage.order,
							order_item=None,
							sequence=(stage.sequence or 0) + 1,
							stage_type='workshop',
							workshop=workshop,
							operation=f"Сборка заказа (стекло) из: {stage.workshop.name if stage.workshop else ''}",
							plan_quantity=completed_qty,
							deadline=timezone.now().date(),
							status='in_progress',
							parallel_group=stage.parallel_group,
						)
					return Response({'status': 'ok', 'stage': stage.id, 'action': 'transferred', 'target_workshop_id': target_workshop_id, 'completed_quantity': completed_qty, 'aggregated': True})
				
				# Иначе (перевод в 2) — ведем обычным образом, но только внутри 2/12
				# Ищем следующий этап по заказу и позиции в выбранном цехе (без учёта sequence)
				next_stage = OrderStage.objects.filter(
					order=stage.order,
					order_item=stage.order_item,
					workshop_id=target_workshop_id,
					stage_type='workshop',
					parallel_group=stage.parallel_group,
				).order_by('sequence').first()
				if next_stage:
					next_stage.plan_quantity += completed_qty
					next_stage.status = 'in_progress'
					next_stage.save(update_fields=['plan_quantity', 'status'])
				else:
					OrderStage.objects.create(
						order=stage.order,
						order_item=stage.order_item,
						sequence=(stage.sequence or 0) + 1,
						stage_type='workshop',
						workshop=workshop,
						operation=f"Передано из: {stage.workshop.name if stage.workshop else ''}",
						plan_quantity=completed_qty,
						deadline=timezone.now().date(),
						status='in_progress',
						parallel_group=stage.parallel_group,
					)
				return Response({'status': 'ok', 'stage': stage.id, 'action': 'transferred', 'target_workshop_id': target_workshop_id, 'completed_quantity': completed_qty})
			
			# Нестеклянные — прежняя логика явного перевода
			# Завершаем текущий этап на указанное количество (частично или полностью)
			stage.confirm_stage(completed_qty)
			# Явно создаём/активируем этап в выбранном цехе
			from apps.operations.workshops.models import Workshop
			workshop = get_object_or_404(Workshop, pk=target_workshop_id)
			# Ищем следующий этап по заказу и позиции в выбранном цехе (без учёта sequence)
			next_stage = OrderStage.objects.filter(
				order=stage.order,
				order_item=stage.order_item,
				workshop=workshop,
				stage_type='workshop',
				parallel_group=stage.parallel_group,
			).order_by('sequence').first()
			if next_stage:
				next_stage.plan_quantity += completed_qty
				next_stage.status = 'in_progress'
				next_stage.save()
			else:
				# Создаём новый этап в выбранном цехе
				OrderStage.objects.create(
					order=stage.order,
					order_item=stage.order_item,
					sequence=stage.sequence + 1,
					stage_type='workshop',
					workshop=workshop,
					operation=f"Передано из: {stage.workshop.name if stage.workshop else ''}",
					plan_quantity=completed_qty,
					deadline=timezone.now().date(),
					status='in_progress',
					parallel_group=stage.parallel_group,
				)
			return Response({'status': 'ok', 'stage': stage.id, 'action': 'transferred', 'target_workshop_id': int(target_workshop_id), 'completed_quantity': completed_qty})
		
		# Fallback: прежнее поведение — перевод по workflow всего плана
		stage.confirm_stage(stage.plan_quantity)
		return Response({'status': 'ok', 'stage': stage.id, 'action': 'transferred'})

class OrderStagePostponeAPIView(APIView):
	permission_classes = [permissions.IsAuthenticated]
	def post(self, request, stage_id):
		stage = get_object_or_404(OrderStage, pk=stage_id)
		# Переносим дедлайн на следующий рабочий день (просто +1 день)
		if stage.deadline:
			from datetime import timedelta
			stage.deadline = stage.deadline + timedelta(days=1)
			stage.save()
			return Response({'status': 'ok', 'stage': stage.id, 'new_deadline': stage.deadline, 'action': 'postponed'})
		return Response({'status': 'error', 'error': 'No deadline set'}, status=400)

class OrderStageNoTransferAPIView(APIView):
	permission_classes = [permissions.IsAuthenticated]
	def post(self, request, stage_id):
		stage = get_object_or_404(OrderStage, pk=stage_id)
		# Фиксируем этап как "не переводить" (например, статус waiting)
		stage.status = 'waiting'
		stage.save()
		return Response({'status': 'ok', 'stage': stage.id, 'action': 'no_transfer'})

class DashboardOverviewAPIView(APIView):
	permission_classes = [permissions.IsAuthenticated]
	def get(self, request):
		# Доход — сумма (цена продукта * количество) по всем позициям заявок
		total_income = OrderItem.objects.aggregate(total=Sum(F('product__price') * F('quantity')))['total'] or 0
		# Продажи — сумма quantity по всем позициям
		product_sales = OrderItem.objects.aggregate(total=Sum('quantity'))['total'] or 0
		# Брак — сумма quantity по всем OrderDefect + сумма defective_quantity по всем EmployeeTask
		order_defects_total = OrderDefect.objects.aggregate(total=Sum('quantity'))['total'] or 0
		employee_tasks_defects_total = EmployeeTask.objects.aggregate(total=Sum('defective_quantity'))['total'] or 0
		defective_products = order_defects_total + employee_tasks_defects_total
		# Сотрудники — всего
		total_employees = User.objects.count()
		return Response({
			'total_income': total_income,
			'product_sales': product_sales,
			'defective_products': defective_products,
			'total_employees': total_employees,
			'user_name': request.user.get_full_name() or request.user.username,
		})

class DashboardRevenueChartAPIView(APIView):
	permission_classes = [permissions.IsAuthenticated]
	def get(self, request):
		period = request.GET.get('period', 'week')
		now = timezone.now()
		if period == 'month':
			days = 30
		elif period == 'year':
			days = 365
		else:
			days = 7
		labels = []
		revenue = []
		defects = []
		orders_count = []
		sales = []
		for i in range(days):
			day = now - timezone.timedelta(days=days - i - 1)
			day_orders = Order.objects.filter(created_at__date=day.date())
			# Доход за день — по позициям, относящимся к заказам этого дня
			day_income = OrderItem.objects.filter(order__in=day_orders).aggregate(total=Sum(F('product__price') * F('quantity')))['total'] or 0
			# Брак: сумма из OrderDefect + сумма defective_quantity из EmployeeTask за этот день
			day_order_defects = OrderDefect.objects.filter(date__date=day.date()).aggregate(total=Sum('quantity'))['total'] or 0
			day_employee_defects = EmployeeTask.objects.filter(created_at__date=day.date()).aggregate(total=Sum('defective_quantity'))['total'] or 0
			day_defects = day_order_defects + day_employee_defects
			day_orders_num = day_orders.count()
			# Продажи — сумма quantities по позициям заказов этого дня
			day_sales = OrderItem.objects.filter(order__in=day_orders).aggregate(total=Sum('quantity'))['total'] or 0
			labels.append(day.strftime('%d.%m'))
			revenue.append(day_income)
			defects.append(day_defects)
			orders_count.append(day_orders_num)
			sales.append(day_sales)
		return Response({
			'labels': labels,
			'revenue': revenue,
			'defects': defects,
			'orders_count': orders_count,
			'sales': sales
		})

class StageViewSet(viewsets.ReadOnlyModelViewSet):
	queryset = OrderStage.objects.select_related(
		'workshop', 
		'order',
		'order__client',
		'order_item',
		'order_item__product',
		'order_item__order'
	).all().order_by('deadline', 'sequence')
	serializer_class = OrderStageSerializer
	permission_classes = [permissions.IsAuthenticated]

	def get_queryset(self):
		qs = super().get_queryset()
		status_param = self.request.query_params.get('status')
		if status_param:
			qs = qs.filter(status=status_param)
		workshop_param = self.request.query_params.get('workshop')
		if workshop_param:
			qs = qs.filter(workshop_id=workshop_param)
		return qs

class PlansMasterView(TemplateView):
    template_name = 'plans_master.html'

class PlansMasterDetailView(TemplateView):
    template_name = 'plans_master_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['stage_id'] = self.kwargs.get('stage_id')
        return context