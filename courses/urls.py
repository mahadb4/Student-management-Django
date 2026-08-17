from django.urls import path
from courses.views import (
    course_create_view,
    course_delete_view,
    course_detail_view,
    course_list_view,
    course_update_view,
)

urlpatterns = [
    path("", course_list_view, name="course_list"),
    path("create/", course_create_view, name="course_create"),
    path("<int:course_id>/", course_detail_view, name="course_detail"),
    path("<int:course_id>/update/", course_update_view, name="course_update"),
    path("<int:course_id>/delete/", course_delete_view, name="course_delete"),
]