from common.messages import Messages
from common.validators import CommonValidator
from departments.models import Department
from teachers.models import Teacher


class CourseValidator:
    def validate(self, data):
        CommonValidator.validate_required(data, [
            "name",
            "code",
            "credits",
            "department",
        ])

        name = data["name"].strip()
        code = data["code"].strip()
        credits = data["credits"]
        department_id = data["department"]

        CommonValidator.validate_length(name, 150, "Course name")
        CommonValidator.validate_length(code, 20, "Course code")
        CommonValidator.validate_positive_number(credits, "Credits")

        semester_number = data.get("semester_number")
        if semester_number not in (None, ""):
            if not isinstance(semester_number, int) or not (1 <= semester_number <= 8):
                raise ValueError(Messages.INVALID_SEMESTER_NUMBER.format(semester_number))

        if not Department.objects.filter(id = department_id, is_active = True).exists():
            raise ValueError(Messages.INVALID_DEPARTMENT.format(department_id))

        teacher_id = data.get("teacher")

        if teacher_id and not Teacher.objects.filter(id = teacher_id, is_active = True).exists():
            raise ValueError(Messages.INVALID_TEACHER.format(teacher_id))
