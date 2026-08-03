from django.urls import path

from .students import students
from .student import student

urlpatterns = [

    path(
        "students/",
        students,
        name="api_students",
    ),

    path(
        "students/<int:student_id>/",
        student,
        name="api_student",
    ),

]