from django.urls import path
from . import views

urlpatterns = [
    path("", views.department_list_view, name = "department_list"),
    path("create/", views.department_create_view, name = "department_create"),
    path("<int:department_id>/", views.department_detail_view, name = "department_detail"),
    path("<int:department_id>/update/", views.department_update_view, name = "department_update"),
    path("<int:department_id>/delete/", views.department_delete_view, name = "department_delete"),
]
