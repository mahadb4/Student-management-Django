from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("students/", include("students.urls")),
    path("teachers/", include("teachers.urls")),
    path("departments/", include("departments.urls")),
    path("courses/", include("courses.urls")),
    path("attendance/", include("attendance.urls")),
    path("enrollments/", include("enrollments.urls")),
    path("course_offerings/", include("course_offerings.urls")),
    path("api/auth/", include("authentication.urls")),
    path("api/", include("students.api.urls")),
    path("api/", include("teachers.api.urls")),
    path("api/", include("departments.api.urls")),
    path("api/", include("courses.api.urls")),
    path("api/", include("attendance.api.urls")),
    path("api/", include("enrollments.api.urls")),
    path("api/", include("course_offerings.api.urls")),
]