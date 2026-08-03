import re

from datetime import date, datetime

from django.core.exceptions import ValidationError
from django.core.validators import validate_email

from students.models import Student


def validate_name(first_name, last_name):

    if not first_name.strip():
        raise ValueError("First name is required.")

    if not last_name.strip():
        raise ValueError("Last name is required.")


def validate_email_address(email, student_id=None):

    try:
        validate_email(email)

    except ValidationError:
        raise ValueError("Enter a valid email address.")

    query = Student.objects.filter(student_email=email)

    if student_id:
        query = query.exclude(id=student_id)

    if query.exists():
        raise ValueError("Email already exists.")


def validate_phone(phone):

    pattern = r"^\+?[0-9()\-\s]+$"

    if not re.match(pattern, phone):
        raise ValueError(
            "Phone number can contain only digits, spaces, '+', '-', and parentheses."
        )

    digits = re.sub(r"\D", "", phone)

    if len(digits) < 10 or len(digits) > 15:
        raise ValueError(
            "Phone number must contain between 10 and 15 digits."
        )


def validate_age(date_of_birth):

    dob = datetime.strptime(
        str(date_of_birth),
        "%Y-%m-%d"
    ).date()

    today = date.today()

    age = today.year - dob.year

    if (today.month, today.day) < (dob.month, dob.day):
        age -= 1

    if age < 16:
        raise ValueError("Student must be at least 16 years old.")


def validate_gender(gender):

    if gender not in ["M", "F"]:
        raise ValueError("Gender must be M or F.")


def validate_student_group(student_group):

    if not student_group.strip():
        raise ValueError("Student group is required.")


def validate_student(data, student_id=None):

    validate_name(
        data["first_name"],
        data["last_name"]
    )

    validate_email_address(
        data["student_email"],
        student_id
    )

    validate_phone(
        data["parents_phone_number"]
    )

    validate_age(
        data["date_of_birth"]
    )

    validate_gender(
        data["gender"]
    )

    validate_student_group(
        data["student_group"]
    )