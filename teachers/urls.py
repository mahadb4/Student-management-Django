from django.urls import path
from . import views

urlpatterns = [
    path("", views.teacher_list_view, name="teacher_list"),
    path("create/", views.teacher_create_view, name="teacher_create"),
    path("<int:teacher_id>/", views.teacher_detail_view, name="teacher_detail"),
    path("<int:teacher_id>/update/", views.teacher_update_view, name="teacher_update"),
    path("<int:teacher_id>/delete/", views.teacher_delete_view, name="teacher_delete"),
]