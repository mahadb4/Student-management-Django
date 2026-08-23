from django.urls import path
from . import views

urlpatterns = [
    path("",views.attendance_list_view,name = "attendance_list"),
    path("mark/<int:offering_id>/",views.attendance_mark_view,name = "attendance_mark"),
]