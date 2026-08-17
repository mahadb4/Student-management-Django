from datetime import date
from common.messages import Messages
from common.validators import CommonValidator

class StudentValidator:
    def validate(self, data):
        CommonValidator.validate_email(data["student_email"])
        CommonValidator.validate_phone(data["parents_phone_number"])
        self.validate_age(data["date_of_birth"])
        self.validate_group(data["student_group"])

    def validate_age(self, date_of_birth):
        if isinstance(date_of_birth, str):
            date_of_birth = date.fromisoformat(date_of_birth)

        today = date.today()
        age = today.year - date_of_birth.year - ((today.month, today.day) < (date_of_birth.month, date_of_birth.day))

        if age < 5:
            raise ValueError(Messages.STUDENT_AGE_MINIMUM)

    def validate_group(self, group):
        if not group or not group.strip():
            raise ValueError(Messages.STUDENT_GROUP_REQUIRED)