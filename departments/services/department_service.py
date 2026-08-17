from common.messages import Messages


class DepartmentService:
    def __init__(self, validator, repository):
        self.validator = validator
        self.repository = repository

    def get(self, department_id):
        return self.repository.get(department_id)

    def get_all(self):
        return self.repository.get_all()

    def create(self, data):
        if not isinstance(data, dict):
            raise ValueError(Messages.REQUEST_DATA_MUST_BE_JSON_OBJECT)

        self.validator.validate(data)

        name = data["name"].strip()
        code = data["code"].strip()

        if self.repository.name_exists(name):
            raise ValueError(Messages.DEPARTMENT_NAME_EXISTS.format(name))

        if self.repository.code_exists(code):
            raise ValueError(Messages.DEPARTMENT_CODE_EXISTS.format(code))

        return self.repository.create(data)

    def update(self, department_id, data, partial = False):
        department = self.repository.get(department_id)

        if not isinstance(data, dict):
            raise ValueError(Messages.REQUEST_DATA_MUST_BE_JSON_OBJECT)

        if partial:
            data = self._merge_data(department, data)

        self.validator.validate(data)

        name = data["name"].strip()
        code = data["code"].strip()

        if self.repository.name_exists(name, department_id):
            raise ValueError(Messages.DEPARTMENT_NAME_EXISTS.format(name))

        if self.repository.code_exists(code, department_id):
            raise ValueError(Messages.DEPARTMENT_CODE_EXISTS.format(code))

        return self.repository.update(department, data)

    def delete(self, department_id):
        self.repository.delete(department_id)

    def _merge_data(self, department, data):
        return {
            "name": data.get("name", department.name),
            "code": data.get("code", department.code),
            "description": data.get("description", department.description),
            "is_active": data.get("is_active", department.is_active),
        }