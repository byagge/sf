from rest_framework import serializers
from .models import EmployeeTask, HelperTask

class EmployeeTaskSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    stage_name = serializers.CharField(source='stage.operation', read_only=True)
    order_name = serializers.CharField(source='stage.order.name', read_only=True)
    workshop_name = serializers.CharField(source='stage.workshop.name', read_only=True)
    product_name = serializers.CharField(source='stage.order_item.product.name', read_only=True)
    product_img = serializers.CharField(source='stage.order_item.product.img', read_only=True)
    
    class Meta:
        model = EmployeeTask
        fields = '__all__'

class HelperTaskSerializer(serializers.ModelSerializer):
    helper_name = serializers.CharField(source='helper.get_full_name', read_only=True)
    employee_task_title = serializers.CharField(source='employee_task.title', read_only=True)
    worker_name = serializers.CharField(source='employee_task.employee.get_full_name', read_only=True)
    operation = serializers.CharField(source='employee_task.stage.operation', read_only=True)
    order_name = serializers.CharField(source='employee_task.stage.order.name', read_only=True)
    product_name = serializers.CharField(source='employee_task.stage.order_item.product.name', read_only=True)
    product_img = serializers.CharField(source='employee_task.stage.order_item.product.img', read_only=True)
    
    class Meta:
        model = HelperTask
        fields = '__all__' 