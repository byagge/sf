from django.urls import path
from .api import (
    MyWorkshopsView, 
    WorkshopEmployeesView, 
    AllWorkshopsView,
    WorkshopMastersView,
    AddWorkshopMasterView,
    RemoveWorkshopMasterView,
    MasterWorkshopsStatsView
)
 
urlpatterns = [
	path('my-workshops/', MyWorkshopsView.as_view()),
	path('employees/', WorkshopEmployeesView.as_view()),
	path('all/', AllWorkshopsView.as_view()),
	path('masters/', WorkshopMastersView.as_view()),
	path('add-master/', AddWorkshopMasterView.as_view()),
	path('remove-master/', RemoveWorkshopMasterView.as_view()),
	path('master-stats/', MasterWorkshopsStatsView.as_view()),
] 