from django.shortcuts import get_object_or_404, redirect, render
from courses.models import Course
from courses.repositories.course_repository import CourseRepository
from courses.services.course_service import CourseService
from courses.services.course_validator import CourseValidator
from departments.models import Department

course_validator = CourseValidator()
course_repository = CourseRepository()
course_service = CourseService(course_validator, course_repository)


def course_list_view(request):
    courses = course_service.get_all()
    return render(request, "courses/course_list.html", {"courses": courses})


def course_detail_view(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    return render(request, "courses/course_detail.html", {"course": course})


def course_create_view(request):
    departments = Department.objects.filter(is_active=True)
    if request.method == "POST":
        data = {
            "name": request.POST.get("name"),
            "code": request.POST.get("code"),
            "description": request.POST.get("description", ""),
            "credits": request.POST.get("credits"),
            "department": request.POST.get("department"),
            "teacher": request.POST.get("teacher") or None,
            "is_active": request.POST.get("is_active"),
        }

        try:
            course_service.create(data)
            return redirect("course_list")
        except ValueError as e:
            return render(request, "courses/course_form.html", {"error": str(e), "data": data, "departments": departments})

    return render(request, "courses/course_form.html", {"departments": departments})


def course_update_view(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    departments = Department.objects.filter(is_active=True)

    if request.method == "POST":
        data = {
            "name": request.POST.get("name"),
            "code": request.POST.get("code"),
            "description": request.POST.get("description", ""),
            "credits": request.POST.get("credits"),
            "department": request.POST.get("department"),
            "teacher": request.POST.get("teacher") or None,
            "is_active": request.POST.get("is_active"),
        }

        try:
            course_service.update(course_id, data)
            return redirect("course_detail", course_id=course_id)
        except ValueError as e:
            return render(request, "courses/course_form.html", {"course": course, "error": str(e), "data": data, "departments": departments})

    return render(request, "courses/course_form.html", {"course": course, "departments": departments})


def course_delete_view(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    if request.method == "POST":
        course_service.delete(course_id)
        return redirect("course_list")

    return render(request, "courses/course_confirm_delete.html", {"course": course})


