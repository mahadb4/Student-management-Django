from django.urls import path
from .student_api import student_api

urlpatterns = [
    path("students/", student_api, name="student_api_list"),
    path("students/<int:student_id>/", student_api, name="student_api_detail"),
]