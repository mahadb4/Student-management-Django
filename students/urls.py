from django.urls import path
from . import views

urlpatterns = [
    path("", views.student_list_view, name = "student_list"),
    path("create/", views.student_create_view, name = "student_create"),
    path("<int:student_id>/update/", views.student_update_view, name = "student_update"),
    path("<int:student_id>/", views.student_detail_view, name = "student_detail"),
    path("<int:student_id>/delete/", views.student_delete_view, name = "student_delete"),
]