from common.messages import Messages
from teachers.services.teacher_validator import TeacherValidator


class TeacherService:
    def __init__(self, validator, repository):
        self.validator = validator
        self.repository = repository

    def get(self, teacher_id):
        return self.repository.get(teacher_id)

    def get_all(self):
        return self.repository.get_all()

    def create(self, data):
        if not isinstance(data, dict):
            raise ValueError(Messages.REQUEST_DATA_MUST_BE_JSON_OBJECT)

        self.validator.validate(data)

        email = data["email"].strip()
        employee_id = data["employee_id"].strip()

        if self.repository.email_exists(email):
            raise ValueError(Messages.EMAIL_ALREADY_EXISTS.format(email))

        if self.repository.employee_id_exists(employee_id):
            raise ValueError(Messages.EMPLOYEE_ID_EXISTS.format(employee_id))

        return self.repository.create(data)

    def update(self, teacher_id, data, partial = False):
        teacher = self.repository.get(teacher_id)

        if not isinstance(data, dict):
            raise ValueError(Messages.REQUEST_DATA_MUST_BE_JSON_OBJECT)

        if partial:
            data = self._merge_data(teacher, data)

        self.validator.validate(data)

        email = data["email"].strip()
        employee_id = data["employee_id"].strip()

        if self.repository.email_exists(email, teacher_id):
            raise ValueError(Messages.EMAIL_ALREADY_EXISTS.format(email))

        if self.repository.employee_id_exists(employee_id, teacher_id):
            raise ValueError(Messages.EMPLOYEE_ID_EXISTS.format(employee_id))

        return self.repository.update(teacher, data)

    def delete(self, teacher_id):
        self.repository.delete(teacher_id)

    def _merge_data(self, teacher, data):
        return {
            "first_name": data.get("first_name", teacher.first_name),
            "last_name": data.get("last_name", teacher.last_name),
            "employee_id": data.get("employee_id", teacher.employee_id),
            "email": data.get("email", teacher.email),
            "phone_number": data.get("phone_number", teacher.phone_number),
            "department": data.get("department", teacher.department_id),
            "designation": data.get("designation", teacher.designation),
            "qualification": data.get("qualification", teacher.qualification),
            "gender": data.get("gender", teacher.gender),
            "date_of_birth": data.get("date_of_birth", teacher.date_of_birth),
            "date_of_joining": data.get("date_of_joining", teacher.date_of_joining),
            "salary": data.get("salary", teacher.salary),
            "address": data.get("address", teacher.address),
            "is_active": data.get("is_active", teacher.is_active),
        }