from django.shortcuts import get_object_or_404, redirect, render
from course_offerings.models import CourseOffering
from enrollments.models import Enrollment
from enrollments.repositories.enrollment_repository import EnrollmentRepository
from enrollments.services.enrollment_service import EnrollmentService
from enrollments.services.enrollment_validator import EnrollmentValidator
from students.models import Student

enrollment_validator = EnrollmentValidator()
enrollment_repository = EnrollmentRepository()
enrollment_service = EnrollmentService(enrollment_validator, enrollment_repository)


def enrollment_list_view(request):
    enrollments = enrollment_service.get_all()
    return render(request, "enrollments/enrollment_list.html", {"enrollments": enrollments})


def enrollment_detail_view(request, enrollment_id):
    enrollment = get_object_or_404(Enrollment, id = enrollment_id)
    return render(request, "enrollments/enrollment_detail.html", {"enrollment": enrollment})


def enrollment_create_view(request):
    students = Student.objects.filter(is_active = True)
    course_offerings = CourseOffering.objects.filter(is_active = True)

    if request.method == "POST":
        data = {
            "student": request.POST.get("student"),
            "course_offering": request.POST.get("course_offering"),
            "status": request.POST.get("status"),
        }

        try:
            enrollment_service.create(data)
            return redirect("enrollment_list")
        except ValueError as e:
            return render(request, "enrollments/enrollment_form.html", {"error": str(e), "data": data, "students": students, "course_offerings": course_offerings})

    return render(request, "enrollments/enrollment_form.html", {"students": students, "course_offerings": course_offerings})


def enrollment_update_view(request, enrollment_id):
    enrollment = get_object_or_404(Enrollment, id = enrollment_id)
    students = Student.objects.filter(is_active = True)
    course_offerings = CourseOffering.objects.filter(is_active = True)

    if request.method == "POST":
        data = {
            "student": request.POST.get("student"),
            "course_offering": request.POST.get("course_offering"),
            "status": request.POST.get("status"),
        }

        try:
            enrollment_service.update(enrollment_id, data)
            return redirect("enrollment_list")
        except ValueError as e:
            return render(request, "enrollments/enrollment_form.html", {"enrollment": enrollment, "error": str(e), "data": data, "students": students, "course_offerings": course_offerings})

    return render(request, "enrollments/enrollment_form.html", {"enrollment": enrollment, "students": students, "course_offerings": course_offerings})


def enrollment_delete_view(request, enrollment_id):
    enrollment = get_object_or_404(Enrollment, id = enrollment_id)

    if request.method == "POST":
        enrollment_service.delete(enrollment_id)
        return redirect("enrollment_list")

    return render(request, "enrollments/enrollment_confirm_delete.html", {"enrollment": enrollment})