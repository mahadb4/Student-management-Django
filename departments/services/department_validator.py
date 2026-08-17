from common.validators import CommonValidator


class DepartmentValidator:
    def validate(self, data):
        CommonValidator.validate_required(data, [
            "name",
            "code",
        ])

        name = data["name"].strip()
        code = data["code"].strip()

        CommonValidator.validate_length(name, 100, "Department name")
        CommonValidator.validate_length(code, 20, "Department code")