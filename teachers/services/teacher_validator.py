from datetime import date, datetime
from common.messages import Messages
from common.validators import CommonValidator
from departments.models import Department
from teachers.models import Teacher


class TeacherValidator:
    def validate(self, data, teacher_id = None):
        CommonValidator.validate_required(data, [
            "first_name",
            "last_name",
            "employee_id",
            "email",
            "phone_number",
            "department",
            "designation",
            "qualification",
            "gender",
            "date_of_birth",
            "date_of_joining",
            "salary",
        ])

        CommonValidator.validate_name(data["first_name"])
        CommonValidator.validate_name(data["last_name"])
        CommonValidator.validate_email(data["email"])
        CommonValidator.validate_phone(data["phone_number"])
        CommonValidator.validate_length(data["employee_id"], 20, "Employee ID")

        date_of_birth = self._parse_date(data["date_of_birth"])
        date_of_joining = self._parse_date(data["date_of_joining"])

        CommonValidator.validate_age(date_of_birth)
        CommonValidator.validate_date_not_in_future(date_of_birth, "Date of birth")
        CommonValidator.validate_date_not_in_future(date_of_joining, "Date of joining")

        department_id = data["department"]

        if not Department.objects.filter(id = department_id, is_active = True).exists():
            raise ValueError(Messages.INVALID_DEPARTMENT.format(department_id))

        CommonValidator.validate_positive_number(data["salary"], "Salary")

        email = Teacher.objects.filter(email = data["email"].strip())
        employee = Teacher.objects.filter(employee_id = data["employee_id"].strip())

        if teacher_id:
            email = email.exclude(id = teacher_id)
            employee = employee.exclude(id = teacher_id)

        if email.exists():
            raise ValueError(Messages.EMAIL_ALREADY_EXISTS.format(data["email"].strip()))

        if employee.exists():
            raise ValueError(Messages.EMPLOYEE_ID_EXISTS.format(data["employee_id"].strip()))

    def _parse_date(self, value):
        if isinstance(value, date):
            return value

        return datetime.strptime(value, "%Y-%m-%d").date()