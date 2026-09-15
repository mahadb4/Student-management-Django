from datetime import date
from common.messages import Messages
from common.validators import CommonValidator
from departments.models import Department
from sections.models import Section

class StudentValidator:
    def validate(self, data):
        CommonValidator.validate_email(data["student_email"])
        CommonValidator.validate_phone(data["parents_phone_number"])
        self.validate_age(data["date_of_birth"])

        department_id = data.get("department")
        section_id = data.get("section")

        # Department/Section are optional on Student (nullable FKs), so only
        # validated when actually provided - same "exists and is active" rule
        # already enforced for Teacher/Course/Section (see teacher_validator.py).
        if department_id and not Department.objects.filter(id = department_id, is_active = True).exists():
            raise ValueError(Messages.INVALID_DEPARTMENT.format(department_id))

        if section_id and not Section.objects.filter(id = section_id, is_deleted = False, is_active = True).exists():
            raise ValueError(Messages.INVALID_SECTION.format(section_id))

        # A crafted request could pass a real Section id alongside an
        # unrelated Department id - the server, not the (already
        # Department-dependent) dropdown, is what must actually enforce that
        # the two belong together.
        if department_id and section_id and not Section.objects.filter(
            id = section_id, department_id = department_id, is_deleted = False, is_active = True,
        ).exists():
            raise ValueError(Messages.SECTION_NOT_IN_DEPARTMENT.format(section_id, department_id))

        # Confirming academic placement (granting the student dashboard
        # access) is only valid once both halves of the assignment exist -
        # never partially, and never without an explicit admin action.
        if data.get("placement_confirmed") and not (department_id and section_id):
            raise ValueError(Messages.PLACEMENT_REQUIRES_DEPARTMENT_AND_SECTION)

    def validate_age(self, date_of_birth):
        if isinstance(date_of_birth, str):
            date_of_birth = date.fromisoformat(date_of_birth)

        today = date.today()
        age = today.year - date_of_birth.year - ((today.month, today.day) 
        < (date_of_birth.month, date_of_birth.day))

        if age < 5:
            raise ValueError(Messages.STUDENT_AGE_MINIMUM)



            