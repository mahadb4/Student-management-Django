from django.shortcuts import get_object_or_404, redirect, render
from students.models import Student
from students.repositories.student_repository import StudentRepository
from students.services.student_service import StudentService
from students.services.student_validator import StudentValidator

student_validator = StudentValidator()
student_repository = StudentRepository()
student_service = StudentService(student_validator, student_repository)


def student_list_view(request):
    students = student_service.get_all()
    return render(request, "students/student_list.html", {"students": students})


def student_detail_view(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    return render(request, "students/student_detail.html", {"student": student})


def student_create_view(request):
    if request.method == "POST":
        data = {
            "first_name": request.POST.get("first_name"),
            "last_name": request.POST.get("last_name"),
            "student_email": request.POST.get("student_email"),
            "parents_phone_number": request.POST.get("parents_phone_number"),
            "date_of_birth": request.POST.get("date_of_birth"),
            "gender": request.POST.get("gender"),
            "address": request.POST.get("address", ""),
            "student_group": request.POST.get("student_group"),
            "teacher": request.POST.get("teacher") or None,
            "is_active": request.POST.get("is_active"),
        }

        try:
            student_service.create(data)
            return redirect("student_list")
        except ValueError as e:
            return render(request, "students/student_form.html", {"error": str(e), "data": data})

    return render(request, "students/student_form.html")


def student_update_view(request, student_id):
    student = get_object_or_404(Student, id=student_id)

    if request.method == "POST":
        data = {
            "first_name": request.POST.get("first_name"),
            "last_name": request.POST.get("last_name"),
            "student_email": request.POST.get("student_email"),
            "parents_phone_number": request.POST.get("parents_phone_number"),
            "date_of_birth": request.POST.get("date_of_birth"),
            "gender": request.POST.get("gender"),
            "address": request.POST.get("address", ""),
            "student_group": request.POST.get("student_group"),
            "teacher": request.POST.get("teacher") or None,
            "is_active": request.POST.get("is_active"),
        }

        try:
            student_service.update(student_id, data)
            return redirect("student_detail", student_id=student_id)
        except ValueError as e:
            return render(request, "students/student_form.html", {"student": student, "error": str(e), "data": data})

    return render(request, "students/student_form.html", {"student": student})


def student_delete_view(request, student_id):
    student = get_object_or_404(Student, id=student_id)

    if request.method == "POST":
        student_service.delete(student_id)
        return redirect("student_list")

    return render(request, "students/student_confirm_delete.html", {"student": student})


