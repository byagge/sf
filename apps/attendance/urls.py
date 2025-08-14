from django.urls import path
from .views import checkin_by_qr, qr_scanner_page, checkout_employee, attendance_overview, attendance_list, attendance_page, recalculate_today_penalties

urlpatterns = [
    path('', attendance_page, name='attendance_main'),
    path('api/checkin/', checkin_by_qr, name='attendance_checkin'),
    path('api/checkout/', checkout_employee, name='attendance_checkout'),
    path('api/overview/', attendance_overview, name='attendance_overview'),
    path('api/list/', attendance_list, name='attendance_list'),
    path('api/recalculate-penalties/', recalculate_today_penalties, name='recalculate_penalties'),
    path('scan/', qr_scanner_page, name='attendance_qr_scanner'),
] 