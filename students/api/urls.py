from django.urls import path
from .student_api import student_api, my_profile_api
from enrollments.api.enrollment_api import my_enrollments_api
from attendance.api.attendance_api import my_attendance_api

urlpatterns = [
    path("students/me/", my_profile_api, name="student_my_profile_api"),
    path("students/me/courses/", my_enrollments_api, name="student_my_courses_api"),
    path("students/me/attendance/", my_attendance_api, name="student_my_attendance_api"),

    path("students/", student_api, name="student_api_list"),
    path("students/<int:student_id>/", student_api, name="student_api_detail"),
]
