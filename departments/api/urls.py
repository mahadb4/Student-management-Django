from django.urls import path
from .department_api import department_api, department_reference_api

urlpatterns = [
    path("departments/reference/", department_reference_api, name = "department_reference_api"),
    path("departments/", department_api, name = "department_api_list"),
    path("departments/<int:department_id>/", department_api, name = "department_api_detail"),
]