from datetime import date, datetime
from common.messages import Messages
from attendance.models import Attendance
from common.validators import CommonValidator
from enrollments.models import Enrollment


class AttendanceValidator:
    def validate(self, data):
        CommonValidator.validate_required(data, [
            "enrollment",
            "date",
            "status",
        ])

        enrollment = data["enrollment"]
        enrollment_id = enrollment.id if hasattr(enrollment, "id") else enrollment

        if not Enrollment.objects.filter(id = enrollment_id).exists():
            raise ValueError(Messages.INVALID_ENROLLMENT.format(enrollment_id))

        attendance_date = self._parse_date(data["date"])
        self.validate_date(attendance_date)
        self.validate_status(data["status"])

    @staticmethod
    def validate_date(value):
        if isinstance(value, str):
            value = datetime.strptime(value, "%Y-%m-%d").date()

        if value > date.today():
            raise ValueError(Messages.ATTENDANCE_DATE_IN_FUTURE)

        return value

    @staticmethod
    def validate_status(status):
        valid = [choice[0] for choice in Attendance.Status.choices]
        if status not in valid:
            raise ValueError(f"Invalid attendance status. Must be one of: {', '.join(valid)}.")

    @staticmethod
    def _parse_date(value):
        if isinstance(value, date):
            return value

        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            raise ValueError(Messages.ATTENDANCE_DATE_INVALID_FORMAT)