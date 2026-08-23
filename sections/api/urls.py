from django.urls import path
from .section_api import section_api

urlpatterns = [
    path("sections/", section_api, name = "section_api_list"),
    path("sections/<int:section_id>/", section_api, name = "section_api_detail"),
]
