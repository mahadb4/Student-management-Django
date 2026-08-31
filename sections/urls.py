from django.urls import path
from . import views

urlpatterns = [
    path("", views.section_list_view, name = "section_list"),
    path("create/", views.section_create_view, name = "section_create"),
    path("<int:section_id>/", views.section_detail_view, name = "section_detail"),
    path("<int:section_id>/update/", views.section_update_view, name = "section_update"),
    path("<int:section_id>/delete/", views.section_delete_view, name = "section_delete"),
]
