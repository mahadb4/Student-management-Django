from django.shortcuts import get_object_or_404, redirect, render
from course_offerings.models import CourseOffering
from course_offerings.repositories.course_offering_repository import CourseOfferingRepository
from course_offerings.services.course_offering_service import CourseOfferingService
from course_offerings.services.course_offering_validator import CourseOfferingValidator
from courses.models import Course
from teachers.models import Teacher

course_offering_validator = CourseOfferingValidator()
course_offering_repository = CourseOfferingRepository()
course_offering_service = CourseOfferingService(course_offering_validator, course_offering_repository)


def course_offering_list_view(request):
    offerings = course_offering_service.get_all()
    return render(request, "course_offerings/course_offering_list.html", {"offerings": offerings})


def course_offering_detail_view(request, offering_id):
    offering = get_object_or_404(CourseOffering, id = offering_id)
    return render(request, "course_offerings/course_offering_detail.html", {"offering": offering})


def course_offering_create_view(request):
    courses = Course.objects.filter(is_active = True)
    teachers = Teacher.objects.filter(is_active = True)

    if request.method == "POST":
        data = {
            "course": request.POST.get("course"),
            "teacher": request.POST.get("teacher"),
            "semester": request.POST.get("semester"),
            "academic_year": request.POST.get("academic_year"),
            "section": request.POST.get("section"),
            "is_active": request.POST.get("is_active"),
        }

        try:
            course_offering_service.create(data)
            return redirect("course_offering_list")
        except ValueError as e:
            return render(request, "course_offerings/course_offering_form.html", {"error": str(e), "data": data, "courses": courses, "teachers": teachers})

    return render(request, "course_offerings/course_offering_form.html", {"courses": courses, "teachers": teachers})


def course_offering_update_view(request, offering_id):
    offering = get_object_or_404(CourseOffering, id = offering_id)
    courses = Course.objects.filter(is_active = True)
    teachers = Teacher.objects.filter(is_active = True)

    if request.method == "POST":
        data = {
            "course": request.POST.get("course"),
            "teacher": request.POST.get("teacher"),
            "semester": request.POST.get("semester"),
            "academic_year": request.POST.get("academic_year"),
            "section": request.POST.get("section"),
            "is_active": request.POST.get("is_active"),
        }

        try:
            course_offering_service.update(offering_id, data)
            return redirect("course_offering_list")
        except ValueError as e:
            return render(request, "course_offerings/course_offering_form.html", {"offering": offering, "error": str(e), "data": data, "courses": courses, "teachers": teachers})

    return render(request, "course_offerings/course_offering_form.html", {"offering": offering, "courses": courses, "teachers": teachers})


def course_offering_delete_view(request, offering_id):
    offering = get_object_or_404(CourseOffering, id = offering_id)

    if request.method == "POST":
        course_offering_service.delete(offering_id)
        return redirect("course_offering_list")

    return render(request, "course_offerings/course_offering_confirm_delete.html", {"offering": offering})