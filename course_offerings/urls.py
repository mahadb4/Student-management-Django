from django.urls import path
from . import views

urlpatterns = [
    path("", views.course_offering_list_view, name="course_offering_list"),
    path("add/", views.course_offering_create_view, name="course_offering_create"),
    path("<int:offering_id>/", views.course_offering_detail_view, name="course_offering_detail"),
    path("<int:offering_id>/edit/", views.course_offering_update_view, name="course_offering_update"),
    path("<int:offering_id>/delete/", views.course_offering_delete_view, name="course_offering_delete"),
]