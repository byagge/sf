from rest_framework import serializers
from .models import Order, OrderStage, OrderDefect, OrderItem, create_order_stages
from apps.clients.models import Client
from apps.products.models import Product
from apps.operations.workshops.models import Workshop
from apps.employee_tasks.serializers import EmployeeTaskSerializer

class ClientFullSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ['id', 'name', 'company', 'phone', 'email', 'address', 'created_at', 'updated_at']
    
    def to_representation(self, instance):
        """Безопасная сериализация с обработкой некорректных данных"""
        try:
            data = super().to_representation(instance)
            
            # Безопасно обрабатываем текстовые поля
            text_fields = ['name', 'company', 'phone', 'email', 'address']
            for field in text_fields:
                if field in data and data[field]:
                    try:
                        # Пытаемся декодировать как UTF-8, если это bytes
                        if isinstance(data[field], bytes):
                            data[field] = data[field].decode('utf-8', errors='replace')
                        # Если это строка, проверяем на корректность
                        elif isinstance(data[field], str):
                            # Проверяем, что строка может быть закодирована в UTF-8
                            data[field].encode('utf-8')
                    except (UnicodeDecodeError, UnicodeEncodeError):
                        # Заменяем некорректные символы
                        if isinstance(data[field], bytes):
                            data[field] = data[field].decode('utf-8', errors='replace')
                        else:
                            data[field] = str(data[field]).encode('utf-8', errors='replace').decode('utf-8')
            
            # Дополнительная защита: проверяем все поля на некорректные данные
            for key, value in data.items():
                if isinstance(value, str) and value:
                    try:
                        # Проверяем, что строка может быть закодирована в UTF-8
                        value.encode('utf-8')
                    except UnicodeEncodeError:
                        # Заменяем некорректные символы
                        data[key] = value.encode('utf-8', errors='replace').decode('utf-8')
                elif isinstance(value, bytes):
                    # Если это bytes, декодируем
                    try:
                        data[key] = value.decode('utf-8', errors='replace')
                    except UnicodeDecodeError:
                        data[key] = value.decode('utf-8', errors='replace')
            
            return data
        except Exception as e:
            # В случае критической ошибки возвращаем минимальную информацию
            print(f"Critical serialization error for client {instance.id}: {e}")
            return {
                'id': instance.id,
                'name': f'Клиент #{instance.id} (ошибка сериализации)',
                'error': 'Ошибка загрузки данных клиента',
                'status': 'error'
            }

class ProductFullSerializer(serializers.ModelSerializer):
    glass_type_display = serializers.CharField(source='get_glass_type_display', read_only=True)
    
    class Meta:
        model = Product
        fields = ['id', 'name', 'type', 'description', 'is_glass', 'glass_type', 'glass_type_display', 'img', 'price', 'created_at', 'updated_at']
    
    def to_representation(self, instance):
        """Безопасная сериализация с обработкой некорректных данных"""
        try:
            data = super().to_representation(instance)
            
            # Безопасно обрабатываем текстовые поля
            text_fields = ['name', 'type', 'description', 'glass_type']
            for field in text_fields:
                if field in data and data[field]:
                    try:
                        # Пытаемся декодировать как UTF-8, если это bytes
                        if isinstance(data[field], bytes):
                            data[field] = data[field].decode('utf-8', errors='replace')
                        # Если это строка, проверяем на корректность
                        elif isinstance(data[field], str):
                            # Проверяем, что строка может быть закодирована в UTF-8
                            data[field].encode('utf-8')
                    except (UnicodeDecodeError, UnicodeEncodeError):
                        # Заменяем некорректные символы
                        if isinstance(data[field], bytes):
                            data[field] = data[field].decode('utf-8', errors='replace')
                        else:
                            data[field] = str(data[field]).encode('utf-8', errors='replace').decode('utf-8')
            
            # Дополнительная защита: проверяем все поля на некорректные данные
            for key, value in data.items():
                if isinstance(value, str) and value:
                    try:
                        # Проверяем, что строка может быть закодирована в UTF-8
                        value.encode('utf-8')
                    except UnicodeEncodeError:
                        # Заменяем некорректные символы
                        data[key] = value.encode('utf-8', errors='replace').decode('utf-8')
                elif isinstance(value, bytes):
                    # Если это bytes, декодируем
                    try:
                        data[key] = value.decode('utf-8', errors='replace')
                    except UnicodeDecodeError:
                        data[key] = value.decode('utf-8', errors='replace')
            
            return data
        except Exception as e:
            # В случае критической ошибки возвращаем минимальную информацию
            print(f"Critical serialization error for product {instance.id}: {e}")
            return {
                'id': instance.id,
                'name': f'Товар #{instance.id} (ошибка сериализации)',
                'error': 'Ошибка загрузки данных товара',
                'status': 'error'
            }

class WorkshopFullSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workshop
        fields = ['id', 'name', 'description', 'is_active', 'created_at', 'updated_at']
    
    def to_representation(self, instance):
        """Безопасная сериализация с обработкой некорректных данных"""
        try:
            data = super().to_representation(instance)
            
            # Безопасно обрабатываем текстовые поля
            text_fields = ['name', 'description']
            for field in text_fields:
                if field in data and data[field]:
                    try:
                        # Пытаемся декодировать как UTF-8, если это bytes
                        if isinstance(data[field], bytes):
                            data[field] = data[field].decode('utf-8', errors='replace')
                        # Если это строка, проверяем на корректность
                        elif isinstance(data[field], str):
                            # Проверяем, что строка может быть закодирована в UTF-8
                            data[field].encode('utf-8')
                    except (UnicodeDecodeError, UnicodeEncodeError):
                        # Заменяем некорректные символы
                        if isinstance(data[field], bytes):
                            data[field] = data[field].decode('utf-8', errors='replace')
                        else:
                            data[field] = str(data[field]).encode('utf-8', errors='replace').decode('utf-8')
            
            # Дополнительная защита: проверяем все поля на некорректные данные
            for key, value in data.items():
                if isinstance(value, str) and value:
                    try:
                        # Проверяем, что строка может быть закодирована в UTF-8
                        value.encode('utf-8')
                    except UnicodeEncodeError:
                        # Заменяем некорректные символы
                        data[key] = value.encode('utf-8', errors='replace').decode('utf-8')
                elif isinstance(value, bytes):
                    # Если это bytes, декодируем
                    try:
                        data[key] = value.decode('utf-8', errors='replace')
                    except UnicodeDecodeError:
                        data[key] = value.decode('utf-8', errors='replace')
            
            return data
        except Exception as e:
            # В случае критической ошибки возвращаем минимальную информацию
            print(f"Critical serialization error for workshop {instance.id}: {e}")
            return {
                'id': instance.id,
                'name': f'Цех #{instance.id} (ошибка сериализации)',
                'error': 'Ошибка загрузки данных цеха',
                'status': 'error'
            }

class WorkshopShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workshop
        fields = ['id', 'name']
    
    def to_representation(self, instance):
        """Безопасная сериализация с обработкой некорректных данных"""
        try:
            data = super().to_representation(instance)
            
            # Безопасно обрабатываем текстовые поля
            if 'name' in data and data['name']:
                try:
                    # Пытаемся декодировать как UTF-8, если это bytes
                    if isinstance(data['name'], bytes):
                        data['name'] = data['name'].decode('utf-8', errors='replace')
                    # Если это строка, проверяем на корректность
                    elif isinstance(data['name'], str):
                        # Проверяем, что строка может быть закодирована в UTF-8
                        data['name'].encode('utf-8')
                except (UnicodeDecodeError, UnicodeEncodeError):
                    # Заменяем некорректные символы
                    if isinstance(data['name'], bytes):
                        data['name'] = data['name'].decode('utf-8', errors='replace')
                    else:
                        data['name'] = str(data['name']).encode('utf-8', errors='replace').decode('utf-8')
            
            # Дополнительная защита: проверяем все поля на некорректные данные
            for key, value in data.items():
                if isinstance(value, str) and value:
                    try:
                        # Проверяем, что строка может быть закодирована в UTF-8
                        value.encode('utf-8')
                    except UnicodeEncodeError:
                        # Заменяем некорректные символы
                        data[key] = value.encode('utf-8', errors='replace').decode('utf-8')
                elif isinstance(value, bytes):
                    # Если это bytes, декодируем
                    try:
                        data[key] = value.decode('utf-8', errors='replace')
                    except UnicodeDecodeError:
                        data[key] = value.decode('utf-8', errors='replace')
            
            return data
        except Exception as e:
            # В случае критической ошибки возвращаем минимальную информацию
            print(f"Critical serialization error for workshop short {instance.id}: {e}")
            return {
                'id': instance.id,
                'name': f'Цех #{instance.id} (ошибка сериализации)',
                'error': 'Ошибка загрузки данных цеха',
                'status': 'error'
            }

class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductFullSerializer(read_only=True, allow_null=True)
    product_id = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all(), write_only=True, source='product', required=False, allow_null=True)
    glass_type_display = serializers.SerializerMethodField()
    order = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = [
            'id', 'product', 'product_id', 'quantity', 'size', 'color',
            'glass_type', 'glass_type_display', 'paint_type', 'paint_color',
            'cnc_specs', 'cutting_specs', 'packaging_notes',
            'glass_cutting_completed', 'glass_cutting_quantity', 'packaging_received_quantity',
            'order'
        ]
    
    def get_glass_type_display(self, obj):
        """Безопасно возвращает отображение типа стекла"""
        try:
            return obj.get_glass_type_display()
        except:
            return obj.glass_type or ""
    
    def get_order(self, obj):
        # Минимальная информация о заказе для отображения в шаблонах
        if not obj.order:
            return None
        try:
            client = obj.order.client
            # Получаем все товары заказа без рекурсивной сериализации
            items = []
            if obj.order.items.exists():
                for item in obj.order.items.all():
                    items.append({
                        'id': item.id,
                        'quantity': item.quantity,
                        'size': item.size,
                        'color': item.color,
                        'product': {
                            'id': item.product.id if item.product else None,
                            'name': item.product.name if item.product else 'Не указан',
                            'is_glass': item.product.is_glass if item.product else False
                        } if item.product else None
                    })
            return {
                'id': obj.order.id,
                'name': obj.order.name,
                'created_at': obj.order.created_at,
                'status_display': obj.order.status_display,
                'comment': obj.order.comment,
                'client': {'id': client.id, 'name': client.name} if client else None,
                'items': items
            }
        except Exception as e:
            # В случае ошибки возвращаем минимальную информацию
            return {
                'id': obj.order.id if obj.order else None,
                'name': obj.order.name if obj.order else 'Не указано',
                'created_at': obj.order.created_at if obj.order else None,
                'status_display': 'Не указан',
                'comment': '',
                'client': None,
                'items': []
            }

    def to_representation(self, instance):
        """Безопасная сериализация с обработкой некорректных данных"""
        try:
            data = super().to_representation(instance)
            
            # Безопасно обрабатываем текстовые поля
            text_fields = ['size', 'color', 'glass_type', 'paint_type', 'paint_color', 'cnc_specs', 'cutting_specs', 'packaging_notes']
            for field in text_fields:
                if field in data and data[field]:
                    try:
                        # Пытаемся декодировать как UTF-8, если это bytes
                        if isinstance(data[field], bytes):
                            data[field] = data[field].decode('utf-8', errors='replace')
                        # Если это строка, проверяем на корректность
                        elif isinstance(data[field], str):
                            # Проверяем, что строка может быть закодирована в UTF-8
                            data[field].encode('utf-8')
                    except (UnicodeDecodeError, UnicodeEncodeError):
                        # Заменяем некорректные символы
                        if isinstance(data[field], bytes):
                            data[field] = data[field].decode('utf-8', errors='replace')
                        else:
                            data[field] = str(data[field]).encode('utf-8', errors='replace').decode('utf-8')
            
            # Дополнительная защита: проверяем все поля на некорректные данные
            for key, value in data.items():
                if isinstance(value, str) and value:
                    try:
                        # Проверяем, что строка может быть закодирована в UTF-8
                        value.encode('utf-8')
                    except UnicodeEncodeError:
                        # Заменяем некорректные символы
                        data[key] = value.encode('utf-8', errors='replace').decode('utf-8')
                elif isinstance(value, bytes):
                    # Если это bytes, декодируем
                    try:
                        data[key] = value.decode('utf-8', errors='replace')
                    except UnicodeDecodeError:
                        data[key] = value.decode('utf-8', errors='replace')
            
            return data
        except Exception as e:
            # В случае критической ошибки возвращаем минимальную информацию
            print(f"Critical serialization error for order item {instance.id}: {e}")
            return {
                'id': instance.id,
                'product': None,
                'quantity': instance.quantity if hasattr(instance, 'quantity') else 0,
                'error': 'Ошибка загрузки данных позиции заказа',
                'status': 'error'
            }

class OrderStageSerializer(serializers.ModelSerializer):
    workshop = WorkshopShortSerializer(read_only=True)
    assigned = EmployeeTaskSerializer(source='employee_tasks', many=True, read_only=True)
    order_name = serializers.CharField(source='order.name', read_only=True)
    order_item = OrderItemSerializer(read_only=True, allow_null=True)
    done_count = serializers.IntegerField(read_only=True)
    defective_count = serializers.IntegerField(read_only=True)
    workshop_info = serializers.SerializerMethodField()
    
    class Meta:
        model = OrderStage
        fields = [
            'id', 'workshop', 'order_name', 'order_item', 'operation', 'sequence', 
            'parallel_group', 'plan_quantity', 'completed_quantity', 'done_count', 
            'defective_count', 'deadline', 'status', 'in_progress', 'defective', 
            'completed', 'date', 'comment', 'assigned', 'workshop_info'
        ]
    
    def get_workshop_info(self, obj):
        """Возвращает информацию для цеха"""
        try:
            return obj.get_workshop_info()
        except:
            return {}
    
    def to_representation(self, instance):
        """Переопределяем для безопасной обработки null значений"""
        try:
            data = super().to_representation(instance)
            # Убеждаемся, что order_item не вызывает ошибок
            if not instance.order_item:
                data['order_item'] = None
            
            # Безопасно обрабатываем текстовые поля
            text_fields = ['operation', 'comment']
            for field in text_fields:
                if field in data and data[field]:
                    try:
                        # Пытаемся декодировать как UTF-8, если это bytes
                        if isinstance(data[field], bytes):
                            data[field] = data[field].decode('utf-8', errors='replace')
                        # Если это строка, проверяем на корректность
                        elif isinstance(data[field], str):
                            # Проверяем, что строка может быть закодирована в UTF-8
                            data[field].encode('utf-8')
                    except (UnicodeDecodeError, UnicodeEncodeError):
                        # Заменяем некорректные символы
                        if isinstance(data[field], bytes):
                            data[field] = data[field].decode('utf-8', errors='replace')
                        else:
                            data[field] = str(data[field]).encode('utf-8', errors='replace').decode('utf-8')
            
            # Дополнительная защита: проверяем все поля на некорректные данные
            for key, value in data.items():
                if isinstance(value, str) and value:
                    try:
                        # Проверяем, что строка может быть закодирована в UTF-8
                        value.encode('utf-8')
                    except UnicodeEncodeError:
                        # Заменяем некорректные символы
                        data[key] = value.encode('utf-8', errors='replace').decode('utf-8')
                elif isinstance(value, bytes):
                    # Если это bytes, декодируем
                    try:
                        data[key] = value.decode('utf-8', errors='replace')
                    except UnicodeDecodeError:
                        data[key] = value.decode('utf-8', errors='replace')
            
            return data
        except Exception as e:
            # В случае критической ошибки возвращаем минимальную информацию
            print(f"Critical serialization error for order stage {instance.id}: {e}")
            return {
                'id': instance.id,
                'operation': 'Ошибка загрузки этапа',
                'error': 'Ошибка загрузки данных этапа',
                'status': 'error'
            }

class OrderDefectSerializer(serializers.ModelSerializer):
    workshop = WorkshopFullSerializer(read_only=True)
    class Meta:
        model = OrderDefect
        fields = ['id', 'workshop', 'quantity', 'date', 'comment']

class OrderSerializer(serializers.ModelSerializer):
    client = ClientFullSerializer(read_only=True)
    product = ProductFullSerializer(read_only=True)
    client_id = serializers.PrimaryKeyRelatedField(queryset=Client.objects.all(), write_only=True, source='client')
    product_id = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all(), write_only=True, source='product', required=False, allow_null=True)
    workshop = WorkshopFullSerializer(read_only=True)
    stages = OrderStageSerializer(many=True, read_only=True)
    defects = OrderDefectSerializer(source='order_defects', many=True, read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    items_data = OrderItemSerializer(many=True, write_only=True, required=False, source='items')
    total_done_count = serializers.IntegerField(read_only=True)
    total_defective_count = serializers.IntegerField(read_only=True)
    status_display = serializers.CharField(read_only=True)
    total_quantity = serializers.IntegerField(read_only=True)
    has_glass_items = serializers.BooleanField(read_only=True)
    glass_items = serializers.SerializerMethodField()
    regular_items = serializers.SerializerMethodField()
    
    # Добавляем безопасные поля
    safe_name = serializers.CharField(source='safe_name', read_only=True)
    safe_comment = serializers.CharField(source='safe_comment', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'name', 'safe_name', 'safe_comment', 'client', 'client_id', 'workshop', 'product', 'product_id', 
            'quantity', 'status', 'status_display', 'expenses', 'comment', 'created_at', 
            'stages', 'defects', 'items', 'items_data', 'total_done_count', 
            'total_defective_count', 'total_quantity', 'has_glass_items', 'glass_items', 'regular_items'
        ]

    def get_glass_items(self, obj):
        return [OrderItemSerializer(item).data for item in obj.glass_items]

    def get_regular_items(self, obj):
        return [OrderItemSerializer(item).data for item in obj.regular_items]

    def to_representation(self, instance):
        """Безопасная сериализация с обработкой некорректных данных"""
        try:
            data = super().to_representation(instance)
            
            # Используем безопасные поля если они доступны
            if hasattr(instance, 'safe_name') and instance.safe_name:
                data['name'] = instance.safe_name
            if hasattr(instance, 'safe_comment') and instance.safe_comment is not None:
                data['comment'] = instance.safe_comment
            
            # Безопасно обрабатываем текстовые поля, которые могут содержать некорректные символы
            text_fields = ['name', 'comment']
            for field in text_fields:
                if field in data and data[field]:
                    try:
                        # Пытаемся декодировать как UTF-8, если это bytes
                        if isinstance(data[field], bytes):
                            data[field] = data[field].decode('utf-8', errors='replace')
                        # Если это строка, проверяем на корректность
                        elif isinstance(data[field], str):
                            # Проверяем, что строка может быть закодирована в UTF-8
                            data[field].encode('utf-8')
                    except (UnicodeDecodeError, UnicodeEncodeError):
                        # Заменяем некорректные символы
                        if isinstance(data[field], bytes):
                            data[field] = data[field].decode('utf-8', errors='replace')
                        else:
                            data[field] = str(data[field]).encode('utf-8', errors='replace').decode('utf-8')
            
            # Дополнительная защита: проверяем все поля на некорректные данные
            for key, value in data.items():
                if isinstance(value, str) and value:
                    try:
                        # Проверяем, что строка может быть закодирована в UTF-8
                        value.encode('utf-8')
                    except UnicodeEncodeError:
                        # Заменяем некорректные символы
                        data[key] = value.encode('utf-8', errors='replace').decode('utf-8')
                elif isinstance(value, bytes):
                    # Если это bytes, декодируем
                    try:
                        data[key] = value.decode('utf-8', errors='replace')
                    except UnicodeDecodeError:
                        data[key] = value.decode('utf-8', errors='replace')
            
            return data
        except Exception as e:
            # В случае критической ошибки возвращаем минимальную информацию
            print(f"Critical serialization error for order {instance.id}: {e}")
            return {
                'id': instance.id,
                'name': f'Заказ #{instance.id} (ошибка сериализации)',
                'error': 'Ошибка загрузки данных заказа',
                'status': 'error'
            }

    def validate(self, attrs):
        # Для создания заказа требуем либо items, либо product+quantity
        if self.instance is None:  # Создание нового заказа
            items = self.initial_data.get('items') or self.initial_data.get('items_data')
            product = attrs.get('product')
            quantity = attrs.get('quantity')
            if not items and not (product and quantity):
                raise serializers.ValidationError('Нужно указать либо product_id и quantity, либо список items.')
        
        # Для обновления заказа валидация не требуется
        return attrs

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        order = Order.objects.create(**validated_data)
        # If items provided, create them; otherwise legacy single product mapping as one item for consistency
        if items_data:
            for item in items_data:
                OrderItem.objects.create(order=order, **item)
            # Ensure stages exist now that we know total quantity
            if not order.stages.exists():
                create_order_stages(order)
        elif order.product and order.quantity:
            OrderItem.objects.create(order=order, product=order.product, quantity=order.quantity)
        return order

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', [])
        
        # Обновляем основные поля заказа (только те, которые есть в модели)
        allowed_fields = ['name', 'client', 'status', 'comment']
        for attr, value in validated_data.items():
            if attr in allowed_fields and hasattr(instance, attr):
                setattr(instance, attr, value)
        instance.save()
        
        # Обновляем товары заказа только если переданы новые данные
        if items_data is not None:
            # Удаляем старые товары
            instance.items.all().delete()
            # Создаем новые товары
            for item in items_data:
                OrderItem.objects.create(order=instance, **item)
            # Пересоздаем этапы если нужно
            if not instance.stages.exists():
                try:
                    create_order_stages(instance)
                except Exception as e:
                    print(f"Warning: Error creating order stages in serializer: {e}")
                    # Продолжаем выполнение, этапы не критичны
        
        return instance

class OrderStageConfirmSerializer(serializers.Serializer):
    completed_quantity = serializers.IntegerField(min_value=0) 