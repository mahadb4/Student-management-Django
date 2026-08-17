from django.shortcuts import get_object_or_404, redirect, render
from departments.models import Department
from departments.repositories.department_repository import DepartmentRepository
from departments.services.department_service import DepartmentService
from departments.services.department_validator import DepartmentValidator

department_validator = DepartmentValidator()
department_repository = DepartmentRepository()
department_service = DepartmentService(department_validator, department_repository)


def department_list_view(request):
    departments = department_service.get_all()
    return render(request, "departments/department_list.html", {"departments": departments})


def department_detail_view(request, department_id):
    department = get_object_or_404(Department, id=department_id)
    return render(request, "departments/department_detail.html", {"department": department})


def department_create_view(request):
    if request.method == "POST":
        data = {
            "name": request.POST.get("name"),
            "code": request.POST.get("code"),
            "description": request.POST.get("description", ""),
            "is_active": request.POST.get("is_active"),
        }

        try:
            department_service.create(data)
            return redirect("department_list")
        except ValueError as e:
            return render(request, "departments/department_form.html", {"error": str(e), "data": data})

    return render(request, "departments/department_form.html")


def department_update_view(request, department_id):
    department = get_object_or_404(Department, id=department_id)

    if request.method == "POST":
        data = {
            "name": request.POST.get("name"),
            "code": request.POST.get("code"),
            "description": request.POST.get("description", ""),
            "is_active": request.POST.get("is_active"),
        }

        try:
            department_service.update(department_id, data)
            return redirect("department_detail", department_id=department_id)
        except ValueError as e:
            return render(request, "departments/department_form.html", {"department": department, "error": str(e), "data": data})

    return render(request, "departments/department_form.html", {"department": department})


def department_delete_view(request, department_id):
    department = get_object_or_404(Department, id=department_id)

    if request.method == "POST":
        department_service.delete(department_id)
        return redirect("department_list")

    return render(request, "departments/department_confirm_delete.html", {"department": department})