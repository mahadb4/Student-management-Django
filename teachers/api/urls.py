from django.urls import path
from .teacher_api import (
    teacher_api, my_profile_api, my_students_api, my_dashboard_api, teacher_reference_api,
    my_profile_picture_upload_url_api, my_profile_picture_confirm_api, my_profile_picture_api,
    teacher_profile_picture_api,
)
from course_offerings.api.course_offering_api import my_course_offerings_api
from attendance.api.attendance_api import my_attendance_api

urlpatterns = [
    path("teachers/me/", my_profile_api, name = "teacher_my_profile_api"),
    path("teachers/me/dashboard/", my_dashboard_api, name = "teacher_my_dashboard_api"),
    path("teachers/me/courses/", my_course_offerings_api, name = "teacher_my_courses_api"),
    path("teachers/me/students/", my_students_api, name = "teacher_my_students_api"),
    path("teachers/me/attendance/", my_attendance_api, name = "teacher_my_attendance_api"),
    path("teachers/me/profile-picture-upload-url/", my_profile_picture_upload_url_api, name = "teacher_my_profile_picture_upload_url_api"),
    path("teachers/me/profile-picture-confirm/", my_profile_picture_confirm_api, name = "teacher_my_profile_picture_confirm_api"),
    path("teachers/me/profile-picture/", my_profile_picture_api, name = "teacher_my_profile_picture_api"),

    path("teachers/reference/", teacher_reference_api, name = "teacher_reference_api"),
    path("teachers/", teacher_api, name = "api_teachers"),
    path("teachers/<int:teacher_id>/profile-picture/", teacher_profile_picture_api, name = "teacher_profile_picture_api"),
    path("teachers/<int:teacher_id>/", teacher_api, name = "api_teacher"),
]
