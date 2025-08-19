from django.shortcuts import render, redirect
from django.http import HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from apps.users.models import User

# Create your views here.

@login_required
def dashboard(request):
    user = request.user
    user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
    is_mobile = any(m in user_agent for m in ['android', 'iphone', 'ipad', 'mobile', 'opera mini', 'blackberry', 'windows phone'])
    role = getattr(user, 'role', None)

    # Founder/Director: use director dashboard templates
    if role in [User.Role.FOUNDER, User.Role.DIRECTOR]:
        template = 'director/dashboard_mobile.html' if is_mobile else 'director/dashboard.html'
        return render(request, template)

    # Admin: use operations dashboard templates
    elif role == User.Role.ADMIN:
        template = 'odashboard_mobile.html' if is_mobile else 'odashboard.html'
        return render(request, template)

    # Accountant: redirect to finance
    elif role == User.Role.ACCOUNTANT:
        return redirect('/finance/')

    # Master: use workshop templates
    elif role == User.Role.MASTER:
        template = 'workshop_mobile.html' if is_mobile else 'workshop_master.html'
        return render(request, template)

    # Worker: redirect to employee tasks
    elif role == User.Role.WORKER:
        return redirect('/employee_tasks/tasks/')

    # No access otherwise
    return HttpResponseForbidden('Нет доступа к дашборду')


def workshop_dashboard(request):
    user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
    is_mobile = any(m in user_agent for m in ['android', 'iphone', 'ipad', 'mobile', 'opera mini', 'blackberry', 'windows phone'])
    template = 'workshop_mobile.html' if is_mobile else 'workshop_master.html'
    return render(request, template)
