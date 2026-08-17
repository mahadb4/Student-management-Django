from common.messages import Messages


class StudentService:
    def __init__(self, validator, repository):
        self.validator = validator
        self.repository = repository

    def get(self, student_id):
        return self.repository.get(student_id)

    def get_all(self):
        return self.repository.get_all()

    def create(self, data):
        if not isinstance(data, dict):
            raise ValueError(Messages.REQUEST_DATA_MUST_BE_JSON_OBJECT)

        self.validator.validate(data)

        if self.repository.email_exists(data["student_email"]):
            raise ValueError(Messages.EMAIL_ALREADY_EXISTS.format(data["student_email"]))

        return self.repository.create(data)

    def update(self, student_id, data, partial = False):
        student = self.repository.get(student_id)

        if not isinstance(data, dict):
            raise ValueError(Messages.REQUEST_DATA_MUST_BE_JSON_OBJECT)

        if partial:
            data = self._merge_data(student, data)

        self.validator.validate(data)

        if self.repository.email_exists(data["student_email"], student_id):
            raise ValueError(Messages.EMAIL_ALREADY_EXISTS.format(data["student_email"]))

        return self.repository.update(student, data)

    def delete(self, student_id):
        self.repository.delete(student_id)

    def _merge_data(self, student, data):
        return {
            "first_name": data.get("first_name", student.first_name),
            "last_name": data.get("last_name", student.last_name),
            "student_email": data.get("student_email", student.student_email),
            "parents_phone_number": data.get("parents_phone_number", student.parents_phone_number),
            "date_of_birth": data.get("date_of_birth", student.date_of_birth),
            "gender": data.get("gender", student.gender),
            "address": data.get("address", student.address),
            "student_group": data.get("student_group", student.student_group),
            "department": data.get("department", student.department_id),
            "teacher": data.get("teacher", student.teacher_id),
            "is_active": data.get("is_active", student.is_active),
        }