import re
from datetime import date
from common.messages import Messages

class CommonValidator:
    @staticmethod
    def validate_required(data, fields):
        for field in fields:
            value = data.get(field)
            if value is None or not str(value).strip():
                raise ValueError(f"{field.replace('_', ' ').title()} is required.")

    @staticmethod
    def validate_name(name):
        if not name:
            raise ValueError(Messages.NAME_REQUIRED)
        name = name.strip()
        if len(name) > 100:
            raise ValueError(Messages.NAME_TOO_LONG)
        pattern = r"^[A-Za-z]+(?:[ '-][A-Za-z]+)*$"
        if not re.match(pattern, name):
            raise ValueError(Messages.NAME_INVALID_CHARS)

    @staticmethod
    def validate_email(email):
        if not email:
            raise ValueError(Messages.EMAIL_REQUIRED)
        email = email.strip()
        if len(email) > 254:
            raise ValueError(Messages.EMAIL_TOO_LONG)
        pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
        if not re.match(pattern, email):
            raise ValueError(Messages.INVALID_EMAIL)

    @staticmethod
    def validate_phone(phone):
        if not phone:
            raise ValueError(Messages.PHONE_REQUIRED)
        phone = phone.strip()
        pattern = r"^\+?[0-9\s\-\(\)]+$"
        if not re.match(pattern, phone):
            raise ValueError(Messages.PHONE_INVALID_CHARS)
        digits = re.sub(r"\D", "", phone)
        if len(digits) < 7 or len(digits) > 15:
            raise ValueError(Messages.PHONE_INVALID_LENGTH)

    @staticmethod
    def validate_length(value, max_length, field_name):
        if value is None:
            return
        value = str(value).strip()
        if len(value) > max_length:
            raise ValueError(f"{field_name} cannot exceed {max_length} characters.")

    @staticmethod
    def validate_age(date_of_birth, minimum_age=5):
        if not date_of_birth:
            raise ValueError(Messages.DATE_OF_BIRTH_REQUIRED)
        today = date.today()
        age = (
            today.year
            - date_of_birth.year
            - ((today.month, today.day) < (date_of_birth.month, date_of_birth.day))
        )
        if age < minimum_age:
            raise ValueError(f"Age must be at least {minimum_age} years.")

    @staticmethod
    def validate_date_not_in_future(value, field_name):
        if not value:
            raise ValueError(f"{field_name} is required.")
        if value > date.today():
            raise ValueError(f"{field_name} cannot be in the future.")

    @staticmethod
    def validate_positive_number(value, field_name):
        if value is None or value == "":
            raise ValueError(f"{field_name} is required.")
        try:
            value = float(value)
        except (TypeError, ValueError):
            raise ValueError(f"{field_name} must be a valid number.")
        if value <= 0:
            raise ValueError(f"{field_name} must be greater than zero.")

    @staticmethod
    def validate_choice(value, choices, field_name):
        if value not in choices:
            raise ValueError(f"Invalid {field_name}.")