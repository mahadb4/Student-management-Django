from common.messages import Messages
from courses.services.course_validator import CourseValidator


class CourseService:
    def __init__(self, validator, repository):
        self.validator = validator
        self.repository = repository

    def get(self, course_id):
        return self.repository.get(course_id)

    def get_all(self):
        return self.repository.get_all()

    def create(self, data):
        if not isinstance(data, dict):
            raise ValueError(Messages.REQUEST_DATA_MUST_BE_JSON_OBJECT)

        self.validator.validate(data)

        code = data["code"].strip()

        if self.repository.code_exists(code):
            raise ValueError(Messages.COURSE_CODE_EXISTS.format(code))

        return self.repository.create(data)

    def update(self, course_id, data, partial = False):
        course = self.repository.get(course_id)

        if not isinstance(data, dict):
            raise ValueError(Messages.REQUEST_DATA_MUST_BE_JSON_OBJECT)

        if partial:
            data = self._merge_data(course, data)

        self.validator.validate(data)

        code = data["code"].strip()

        if self.repository.code_exists(code, course_id):
            raise ValueError(Messages.COURSE_CODE_EXISTS.format(code))

        return self.repository.update(course, data)

    def delete(self, course_id):
        self.repository.delete(course_id)

    def _merge_data(self, course, data):
        return {
            "name": data.get("name", course.name),
            "code": data.get("code", course.code),
            "description": data.get("description", course.description),
            "credits": data.get("credits", course.credits),
            "department": data.get("department", course.department_id),
            "teacher": data.get("teacher", course.teacher_id),
            "is_active": data.get("is_active", course.is_active),
        }
