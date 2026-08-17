from django.shortcuts import get_object_or_404, redirect, render
from departments.models import Department
from teachers.models import Teacher
from teachers.repositories.teacher_repository import TeacherRepository
from teachers.services.teacher_service import TeacherService
from teachers.services.teacher_validator import TeacherValidator

teacher_validator = TeacherValidator()
teacher_repository = TeacherRepository()
teacher_service = TeacherService(teacher_validator, teacher_repository)


def teacher_list_view(request):
    teachers = teacher_service.get_all()
    return render(request, "teachers/teacher_list.html", {"teachers": teachers})


def teacher_detail_view(request, teacher_id):
    teacher = get_object_or_404(Teacher, id=teacher_id)
    return render(request, "teachers/teacher_detail.html", {"teacher": teacher})


def teacher_create_view(request):
    departments = Department.objects.filter(is_active = True)

    if request.method == "POST":
        data = {
            "first_name": request.POST.get("first_name"),
            "last_name": request.POST.get("last_name"),
            "employee_id": request.POST.get("employee_id"),
            "email": request.POST.get("email"),
            "phone_number": request.POST.get("phone_number"),
            "department": request.POST.get("department"),
            "designation": request.POST.get("designation"),
            "qualification": request.POST.get("qualification"),
            "gender": request.POST.get("gender"),
            "date_of_birth": request.POST.get("date_of_birth"),
            "date_of_joining": request.POST.get("date_of_joining"),
            "salary": request.POST.get("salary"),
            "address": request.POST.get("address", ""),
            "is_active": request.POST.get("is_active"),
        }

        try:
            teacher_service.create(data)
            return redirect("teacher_list")
        except ValueError as e:
            return render(request, "teachers/teacher_form.html", {"error": str(e), "data": data, "departments": departments})

    return render(request, "teachers/teacher_form.html", {"departments": departments})


def teacher_update_view(request, teacher_id):
    teacher = get_object_or_404(Teacher, id = teacher_id)
    departments = Department.objects.filter(is_active = True)

    if request.method == "POST":
        data = {
            "first_name": request.POST.get("first_name"),
            "last_name": request.POST.get("last_name"),
            "employee_id": request.POST.get("employee_id"),
            "email": request.POST.get("email"),
            "phone_number": request.POST.get("phone_number"),
            "department": request.POST.get("department"),
            "designation": request.POST.get("designation"),
            "qualification": request.POST.get("qualification"),
            "gender": request.POST.get("gender"),
            "date_of_birth": request.POST.get("date_of_birth"),
            "date_of_joining": request.POST.get("date_of_joining"),
            "salary": request.POST.get("salary"),
            "address": request.POST.get("address", ""),
            "is_active": request.POST.get("is_active"),
        }

        try:
            teacher_service.update(teacher_id, data)
            return redirect("teacher_detail", teacher_id = teacher_id)
        except ValueError as e:
            return render(request, "teachers/teacher_form.html", {"teacher": teacher, "error": str(e), "data": data, "departments": departments})

    return render(request, "teachers/teacher_form.html", {"teacher": teacher, "departments": departments})


def teacher_delete_view(request, teacher_id):
    teacher = get_object_or_404(Teacher, id = teacher_id)

    if request.method == "POST":
        teacher_service.delete(teacher_id)
        return redirect("teacher_list")

    return render(request, "teachers/teacher_confirm_delete.html", {"teacher": teacher})