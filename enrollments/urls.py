from django.urls import path
from . import views

urlpatterns = [
    path("", views.enrollment_list_view, name="enrollment_list"),
    path("add/", views.enrollment_create_view, name="enrollment_create"),
    path("<int:enrollment_id>/", views.enrollment_detail_view, name="enrollment_detail"),
    path("<int:enrollment_id>/edit/", views.enrollment_update_view, name="enrollment_update"),
    path("<int:enrollment_id>/delete/", views.enrollment_delete_view, name="enrollment_delete"),
]