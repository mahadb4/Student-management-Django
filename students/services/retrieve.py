from django.shortcuts import get_object_or_404

from students.models import Student


def get_all_students():

    return Student.objects.all()


def get_student(student_id):

    return get_object_or_404(
        Student,
        id=student_id
    )