from django.shortcuts import get_object_or_404, redirect, render
from sections.models import Section
from sections.repositories.section_repository import SectionRepository
from sections.services.section_service import SectionService
from sections.services.section_validator import SectionValidator

section_validator = SectionValidator()
section_repository = SectionRepository()
section_service = SectionService(section_validator, section_repository)


def section_list_view(request):
    sections = section_service.get_all()
    return render(request, "sections/section_list.html", {"sections": sections})


def section_detail_view(request, section_id):
    section = get_object_or_404(Section, id = section_id)
    return render(request, "sections/section_detail.html", {"section": section})


def section_create_view(request):
    if request.method == "POST":
        data = {
            "name": request.POST.get("name"),
            "department": request.POST.get("department"),
            "semester_number": request.POST.get("semester_number"),
            "academic_year": request.POST.get("academic_year"),
            "is_active": request.POST.get("is_active"),
        }

        try:
            section_service.create(data)
            return redirect("section_list")
        except ValueError as e:
            return render(request, "sections/section_form.html", {"error": str(e), "data": data})

    return render(request, "sections/section_form.html")


def section_update_view(request, section_id):
    section = get_object_or_404(Section, id = section_id)

    if request.method == "POST":
        data = {
            "name": request.POST.get("name"),
            "department": request.POST.get("department"),
            "semester_number": request.POST.get("semester_number"),
            "academic_year": request.POST.get("academic_year"),
            "is_active": request.POST.get("is_active"),
        }

        try:
            section_service.update(section_id, data)
            return redirect("section_detail", section_id = section_id)
        except ValueError as e:
            return render(request, "sections/section_form.html", {"section": section, "error": str(e), "data": data})

    return render(request, "sections/section_form.html", {"section": section})


def section_delete_view(request, section_id):
    section = get_object_or_404(Section, id = section_id)

    if request.method == "POST":
        section_service.delete(section_id)
        return redirect("section_list")

    return render(request, "sections/section_confirm_delete.html", {"section": section})
