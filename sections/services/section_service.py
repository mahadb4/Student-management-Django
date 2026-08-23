from common.messages import Messages


class SectionService:
    def __init__(self, validator, repository):
        self.validator = validator
        self.repository = repository

    def get(self, section_id):
        return self.repository.get(section_id)

    def get_all(self):
        return self.repository.get_all()

    def create(self, data):
        if not isinstance(data, dict):
            raise ValueError(Messages.REQUEST_DATA_MUST_BE_JSON_OBJECT)

        self.validator.validate(data)

        name = data["name"].strip()
        department_id = data["department"]
        semester_number = data["semester_number"]
        academic_year = data["academic_year"]

        if self.repository.section_exists(name, department_id, semester_number, academic_year):
            raise ValueError(Messages.SECTION_EXISTS)

        return self.repository.create(data)

    def update(self, section_id, data, partial = False):
        section = self.repository.get(section_id)

        if not isinstance(data, dict):
            raise ValueError(Messages.REQUEST_DATA_MUST_BE_JSON_OBJECT)

        if partial:
            data = self._merge_data(section, data)

        self.validator.validate(data)

        name = data["name"].strip()
        department_id = data["department"]
        semester_number = data["semester_number"]
        academic_year = data["academic_year"]

        if self.repository.section_exists(name, department_id, semester_number, academic_year, section_id):
            raise ValueError(Messages.SECTION_EXISTS)

        return self.repository.update(section, data)

    def delete(self, section_id):
        self.repository.delete(section_id)

    def _merge_data(self, section, data):
        return {
            "name": data.get("name", section.name),
            "department": data.get("department", section.department_id),
            "semester_number": data.get("semester_number", section.semester_number),
            "academic_year": data.get("academic_year", section.academic_year),
            "is_active": data.get("is_active", section.is_active),
        }
