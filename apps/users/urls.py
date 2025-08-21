from django.urls import path
from .views import LoginView, ProfileView, ProfileAPIView, LogoutView
 
urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('api/profile/', ProfileAPIView.as_view(), name='api-profile'),
] 