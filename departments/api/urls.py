from django.urls import path
from .department_api import department_api

urlpatterns = [
    path("departments/", department_api, name = "department_api_list"),
    path("departments/<int:department_id>/", department_api, name = "department_api_detail"),
]