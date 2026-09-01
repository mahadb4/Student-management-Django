from django.urls import path
from .course_offering_api import course_offering_api, course_offering_reference_api

urlpatterns = [
    path("course_offerings/reference/", course_offering_reference_api, name = "course_offering_reference_api"),
    path("course_offerings/", course_offering_api, name = "course_offering_api_list"),
    path("course_offerings/<int:offering_id>/", course_offering_api, name = "course_offering_api_detail"),
]
