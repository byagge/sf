from django.shortcuts import render
from .models import Workshop
from rest_framework import viewsets
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework import permissions
from apps.users.models import User
from apps.employees.models import EmployeeStatistics, EmployeeTask
from django.db.models import Count, Sum, Avg, Q

# Create your views here.

class WorkshopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workshop
        fields = ['id', 'name', 'description', 'is_active']

class WorkshopViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Workshop.objects.filter(is_active=True)
    serializer_class = WorkshopSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        base_qs = Workshop.objects.filter(is_active=True)
        # Для мастера показываем только его цех и те, которыми он управляет
        if hasattr(user, 'role') and user.role == User.Role.MASTER:
            return base_qs.filter(Q(id=user.workshop_id) | Q(manager=user))
        # Для прочих ролей возвращаем все активные (как и было)
        return base_qs


def workshops_list(request):
    workshops = Workshop.objects.all().order_by('id')
    # Собираем статистику по каждому цеху
    workshops_data = []
    total_employees = 0
    total_productivity = 0
    total_active_tasks = 0
    total_defects = 0
    for w in workshops:
        employees = User.objects.filter(workshop=w, role__in=[User.Role.WORKER, User.Role.MASTER])
        employees_count = employees.count()
        total_employees += employees_count
        # Статистика сотрудников этого цеха
        stats = EmployeeStatistics.objects.filter(employee__in=employees)
        # Производительность за месяц (сумма по всем сотрудникам)
        productivity = stats.aggregate(total=Sum('completed_works'))['total'] or 0
        total_productivity += productivity
        # Браки (сумма по всем сотрудникам)
        defects = stats.aggregate(total=Sum('defects'))['total'] or 0
        total_defects += defects
        # Активные задачи (не выполненные)
        active_tasks = EmployeeTask.objects.filter(employee__in=employees, completed=False).count()
        total_active_tasks += active_tasks
        # Мини-график производительности (суммируем по дням за 7 дней)
        productivity_chart = [0]*7
        for s in stats:
            chart = s.productivity_chart or [0]*7
            for i in range(min(7, len(chart))):
                productivity_chart[i] += chart[i]
        workshops_data.append({
            'id': w.id,
            'name': w.name,
            'description': w.description,
            'manager': w.manager.get_full_name() if w.manager else '—',
            'created_at': w.created_at,
            'updated_at': w.updated_at,
            'employees_count': employees_count,
            'productivity': productivity,
            'defects': defects,
            'active_tasks': active_tasks,
            'productivity_chart': productivity_chart,
        })
    total_workshops = workshops.count()
    avg_productivity = int(total_productivity / total_workshops) if total_workshops else 0
    user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
    is_mobile = any(m in user_agent for m in ['android', 'iphone', 'ipad', 'mobile', 'opera mini', 'blackberry', 'windows phone'])
    template = 'workshops_mobile.html' if is_mobile else 'workshops.html'
    return render(request, template, {
        'workshops': workshops_data,
        'total_workshops': total_workshops,
        'total_employees': total_employees,
        'avg_productivity': avg_productivity,
        'total_active_tasks': total_active_tasks,
        'total_defects': total_defects,
    })
