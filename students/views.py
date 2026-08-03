from django.shortcuts import render, redirect

from students.services.create import create_student
from students.services.retrieve import get_all_students
from students.services.retrieve import get_student
from students.services.update import update_student
from students.services.delete import delete_student


def student_create_view(request):

    if request.method == "POST":

        try:

            create_student(request.POST)

            return redirect("student_list")

        except Exception as e:

            return render(
                request,
                "students/student_form.html",
                {
                    "error": str(e)
                },
            )

    return render(
        request,
        "students/student_form.html",
    )


def student_list_view(request):

    students = get_all_students()

    return render(
        request,
        "students/student_list.html",
        {
            "students": students
        },
    )


def student_update_view(request, student_id):

    student = get_student(student_id)

    if request.method == "POST":

        try:

            update_student(
                student_id,
                request.POST,
            )

            return redirect("student_list")

        except Exception as e:

            return render(
                request,
                "students/student_form.html",
                {
                    "student": student,
                    "error": str(e),
                },
            )

    return render(
        request,
        "students/student_form.html",
        {
            "student": student,
        },
    )


def student_delete_view(request, student_id):

    delete_student(student_id)

    return redirect("student_list")