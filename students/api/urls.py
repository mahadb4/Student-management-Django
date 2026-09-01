from django.urls import path
from .student_api import student_api, my_profile_api, my_summary_api, student_reference_api
from enrollments.api.enrollment_api import my_enrollments_api, my_enrollments_reference_api
from attendance.api.attendance_api import my_student_attendance_api

urlpatterns = [
    path("students/me/", my_profile_api, name = "student_my_profile_api"),
    path("students/me/summary/", my_summary_api, name = "student_my_summary_api"),
    path("students/me/courses/reference/", my_enrollments_reference_api, name = "student_my_courses_reference_api"),
    path("students/me/courses/", my_enrollments_api, name = "student_my_courses_api"),
    path("students/me/attendance/", my_student_attendance_api, name = "student_my_attendance_api"),
    path("students/reference/", student_reference_api, name = "student_reference_api"),
    path("students/", student_api, name = "student_api_list"),
    path("students/<int:student_id>/", student_api, name = "student_api_detail"),
]
