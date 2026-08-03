from .retrieve import get_student
from .validation import validate_student


def update_student(student_id, data):

    student = get_student(student_id)

    validate_student(
        data,
        student_id
    )

    student.first_name = data["first_name"]
    student.last_name = data["last_name"]
    student.student_email = data["student_email"]
    student.parents_phone_number = data["parents_phone_number"]
    student.date_of_birth = data["date_of_birth"]
    student.gender = data["gender"]
    student.address = data["address"]
    student.student_group = data["student_group"]
    student.is_active = True if data.get("is_active") else False

    student.save()

    return student