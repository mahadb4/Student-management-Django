from django.urls import path
from .course_api import course_api, course_reference_api

urlpatterns = [
    path("courses/reference/", course_reference_api, name = "course_reference_api"),
    path("courses/", course_api, name = "course_api_list"),
    path("courses/<int:course_id>/", course_api, name = "course_api_detail"),
]