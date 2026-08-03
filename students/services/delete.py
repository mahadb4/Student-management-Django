from .retrieve import get_student


def delete_student(student_id):

    student = get_student(student_id)

    student.delete()

    return True