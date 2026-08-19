from common.messages import Messages


class UserValidator:
    PUBLIC_REGISTRATION_ROLES = ["student", "teacher", "staff"]

    def validate_register(self, data):
        self._validate_json_object(data)
        self._validate_required_fields(data)
        self._validate_name(data["name"])
        self._validate_email(data["email"])
        self._validate_password(data["password"])
        self._validate_role(data["role"])

    def validate_login(self, data):
        self._validate_json_object(data)

        if not data.get("email"):
            raise ValueError(Messages.EMAIL_REQUIRED)

        if not data.get("password"):
            raise ValueError(Messages.PASSWORD_REQUIRED)

        self._validate_email(data["email"])

    def _validate_json_object(self, data):
        if not isinstance(data, dict):
            raise ValueError(Messages.REQUEST_DATA_MUST_BE_JSON_OBJECT)

    def _validate_required_fields(self, data):
        required_fields = ["name", "email", "password", "role"]

        for field in required_fields:
            if not data.get(field):
                raise ValueError(f"{field.capitalize()} is required.")

    def _validate_name(self, name):
        name = name.strip()

        if len(name) > 100:
            raise ValueError(Messages.NAME_TOO_LONG)

    def _validate_email(self, email):
        email = email.strip()

        if len(email) > 254:
            raise ValueError(Messages.EMAIL_TOO_LONG)

        if "@" not in email:
            raise ValueError(Messages.INVALID_EMAIL)

    def _validate_password(self, password):
        if len(password) < 8:
            raise ValueError(Messages.PASSWORD_TOO_SHORT)

    def _validate_role(self, role):
        if role not in self.PUBLIC_REGISTRATION_ROLES:
            raise ValueError(
                "Invalid role. Public registration only allows: student, teacher, staff."
            )