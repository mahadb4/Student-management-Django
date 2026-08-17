from django.urls import path
from .attendance_api import attendance_api

urlpatterns = [
    path("attendance/", attendance_api, name="attendance_api_list"),
    path("attendance/<int:attendance_id>/", attendance_api, name="attendance_api_detail"),
]
