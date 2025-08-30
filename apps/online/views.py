from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from .models import UserActivity
from django.contrib.auth import get_user_model

User = get_user_model()

def is_staff_user(user):
    """Проверка, является ли пользователь staff"""
    return user.is_staff

@login_required
@user_passes_test(is_staff_user, login_url='/accounts/login/')
def online_users_view(request):
    """Отображение всех онлайн пользователей"""
    if not request.user.is_staff:
        messages.error(request, 'У вас нет доступа к этой странице.')
        return redirect('home')
    
    # Обновляем активность текущего пользователя
    UserActivity.update_user_activity(request.user)
    
    # Получаем всех онлайн пользователей
    online_users = UserActivity.get_online_users()
    
    context = {
        'online_users': online_users,
        'total_online': online_users.count(),
        'current_time': timezone.now(),
    }
    
    return render(request, 'online/online_users.html', context)

@login_required
@user_passes_test(is_staff_user)
def online_users_api(request):
    """API для получения списка онлайн пользователей"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    online_users = UserActivity.get_online_users()
    
    users_data = []
    for activity in online_users:
        users_data.append({
            'id': activity.user.id,
            'username': activity.user.username,
            'first_name': activity.user.first_name or '',
            'last_name': activity.user.last_name or '',
            'email': activity.user.email,
            'last_seen': activity.last_seen.isoformat(),
            'is_staff': activity.user.is_staff,
            'is_superuser': activity.user.is_superuser,
        })
    
    return JsonResponse({
        'users': users_data,
        'total': len(users_data),
        'timestamp': timezone.now().isoformat()
    })

@login_required
@user_passes_test(is_staff_user)
def user_activity_detail(request, user_id):
    """Детальная информация об активности пользователя"""
    if not request.user.is_staff:
        messages.error(request, 'У вас нет доступа к этой странице.')
        return redirect('home')
    
    try:
        user = User.objects.get(id=user_id)
        activities = UserActivity.objects.filter(user=user).order_by('-last_seen')[:50]
        
        context = {
            'target_user': user,
            'activities': activities,
            'total_activities': activities.count(),
        }
        
        return render(request, 'online/user_activity_detail.html', context)
        
    except User.DoesNotExist:
        messages.error(request, 'Пользователь не найден.')
        return redirect('online:online_users')
