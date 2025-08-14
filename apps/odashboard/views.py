from django.shortcuts import render
from django.http import HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from apps.users.models import User

# Create your views here.

@login_required
def dashboard(request):
    user = request.user
    user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
    is_mobile = any(m in user_agent for m in ['android', 'iphone', 'ipad', 'mobile', 'opera mini', 'blackberry', 'windows phone'])

    if user.role in [User.Role.FOUNDER, User.Role.DIRECTOR, User.Role.ADMIN, User.Role.ACCOUNTANT]:
        template = 'odashboard_mobile.html' if is_mobile else 'odashboard.html'
    elif user.role == User.Role.MASTER:
        template = 'workshop_mobile.html' if is_mobile else 'workshop_master.html'
    else:
        return HttpResponseForbidden('Нет доступа к дашборду')
    return render(request, template)


def workshop_dashboard(request):
    user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
    is_mobile = any(m in user_agent for m in ['android', 'iphone', 'ipad', 'mobile', 'opera mini', 'blackberry', 'windows phone'])
    template = 'workshop_mobile.html' if is_mobile else 'workshop_master.html'
    return render(request, template)
