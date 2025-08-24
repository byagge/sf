from django.urls import path
from .api import (
    MyWorkshopsView, 
    WorkshopEmployeesView, 
    AllWorkshopsView,
    WorkshopMastersView,
    AddWorkshopMasterView,
    RemoveWorkshopMasterView
)
 
urlpatterns = [
	path('api/my-workshops/', MyWorkshopsView.as_view()),
	path('api/employees/', WorkshopEmployeesView.as_view()),
	path('api/all/', AllWorkshopsView.as_view()),
	path('api/masters/', WorkshopMastersView.as_view()),
	path('api/add-master/', AddWorkshopMasterView.as_view()),
	path('api/remove-master/', RemoveWorkshopMasterView.as_view()),
] 