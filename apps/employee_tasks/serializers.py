from rest_framework import serializers
from .models import EmployeeTask

class EmployeeTaskSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    done_quantity = serializers.SerializerMethodField()
    class Meta:
        model = EmployeeTask
        fields = ['id', 'stage', 'employee', 'employee_name', 'quantity', 'completed_quantity', 'defective_quantity', 'done_quantity']

    def get_done_quantity(self, obj):
        # Если задача выполнена, считаем всё количество сделанным, иначе 0
        return obj.quantity if getattr(obj, 'is_completed', False) else 0

    def get_employee_name(self, obj):
        if obj.employee:
            # Попробовать get_full_name, иначе first_name + last_name, иначе username
            if hasattr(obj.employee, 'get_full_name'):
                name = obj.employee.get_full_name()
                if name:
                    return name
            first = getattr(obj.employee, 'first_name', '')
            last = getattr(obj.employee, 'last_name', '')
            if first or last:
                return f'{first} {last}'.strip()
            return getattr(obj.employee, 'username', str(obj.employee.pk))
        return '' 