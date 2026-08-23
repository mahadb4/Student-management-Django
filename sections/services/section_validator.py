from common.messages import Messages
from common.validators import CommonValidator
from departments.models import Department


class SectionValidator:
    def validate(self, data):
        CommonValidator.validate_required(data, [
            "name",
            "department",
            "semester_number",
            "academic_year",
        ])

        name = data["name"].strip()
        department_id = data["department"]
        semester_number = data["semester_number"]
        academic_year = data["academic_year"]

        CommonValidator.validate_length(name, 50, "Section name")
        CommonValidator.validate_positive_number(semester_number, "Semester number")
        CommonValidator.validate_positive_number(academic_year, "Academic year")

        if not Department.objects.filter(id = department_id, is_active = True).exists():
            raise ValueError(Messages.INVALID_DEPARTMENT.format(department_id))
