from django.urls import path
from .teacher_api import teacher_api

urlpatterns = [
    path("teachers/", teacher_api, name="api_teachers"),
    path("teachers/<int:teacher_id>/", teacher_api, name="api_teacher"),
    
]