from django.urls import path
from .course_api import course_api

urlpatterns = [
    path("courses/", course_api, name = "course_api_list"),
    path("courses/<int:course_id>/", course_api, name = "course_api_detail"),
]