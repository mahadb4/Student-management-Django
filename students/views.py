from django.shortcuts import render
from .services.student_service import StudentService


def student_form(request):

    if request.method == "POST":
        StudentService.create_student(request.POST)

    return render(request, "students/student_form.html")


def student_list(request):

    students = StudentService.get_all_students()

    return render(
        request,
        "students/student_list.html",
        {"students": students},
    )