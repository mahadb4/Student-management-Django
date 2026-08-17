from django.urls import path
from .enrollment_api import enrollment_api

urlpatterns = [
    path("enrollments/", enrollment_api, name="enrollment_api_list"),
    path("enrollments/<int:enrollment_id>/", enrollment_api, name="enrollment_api_detail"),
]
