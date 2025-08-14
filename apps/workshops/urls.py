from django.urls import path
from .api import MyWorkshopsView, WorkshopEmployeesView
 
urlpatterns = [
    path('api/my-workshops/', MyWorkshopsView.as_view()),
    path('api/employees/', WorkshopEmployeesView.as_view()),
] 