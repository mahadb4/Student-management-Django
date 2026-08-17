from common.messages import Messages


class CourseOfferingService:
    def __init__(self, validator, repository):
        self.validator = validator
        self.repository = repository

    def get(self, offering_id):
        return self.repository.get(offering_id)

    def get_all(self):
        return self.repository.get_all()

    def create(self, data):
        if not isinstance(data, dict):
            raise ValueError(Messages.REQUEST_DATA_MUST_BE_JSON_OBJECT)

        self.validator.validate(data)

        course_id = data["course"]
        teacher_id = data["teacher"]
        semester = data["semester"]
        academic_year = data["academic_year"]
        section = data["section"].strip()

        if self.repository.course_offering_exists(course_id, teacher_id, semester, academic_year, section):
            raise ValueError(Messages.COURSE_OFFERING_EXISTS)

        return self.repository.create(data)

    def update(self, offering_id, data, partial = False):
        offering = self.repository.get(offering_id)

        if not isinstance(data, dict):
            raise ValueError(Messages.REQUEST_DATA_MUST_BE_JSON_OBJECT)

        if partial:
            data = self._merge_data(offering, data)

        self.validator.validate(data)

        course_id = data["course"]
        teacher_id = data["teacher"]
        semester = data["semester"]
        academic_year = data["academic_year"]
        section = data["section"].strip()

        if self.repository.course_offering_exists(course_id, teacher_id, semester, academic_year, section, offering_id):
            raise ValueError(Messages.COURSE_OFFERING_EXISTS)

        return self.repository.update(offering, data)

    def delete(self, offering_id):
        self.repository.delete(offering_id)

    def _merge_data(self, offering, data):
        return {
            "course": data.get("course", offering.course_id),
            "teacher": data.get("teacher", offering.teacher_id),
            "semester": data.get("semester", offering.semester),
            "academic_year": data.get("academic_year", offering.academic_year),
            "section": data.get("section", offering.section),
            "is_active": data.get("is_active", offering.is_active),
        }