from datetime import date,datetime
from django.db.models import Q
from common.messages import Messages
from common.validators import CommonValidator
from attendance.models import Attendance
from enrollments.models import Enrollment

class AttendanceValidator:
    def validate(self,data):
        CommonValidator.validate_required(data,["enrollment_id","date","status"])
        enrollment_id = data["enrollment_id"]

        # Kept consistent with AttendanceService.get_active_enrollment - see
        # that method's comment for why course/teacher/section are re-checked
        # instead of only trusting course_offering.is_active.
        if not Enrollment.objects.filter(
            id = enrollment_id,
            status = Enrollment.Status.ACTIVE,
            is_deleted = False,
            student__is_deleted = False,
            student__is_active = True,
            course_offering__is_deleted = False,
            course_offering__is_active = True,
            course_offering__course__is_active = True,
            course_offering__teacher__is_active = True,
        ).filter(
            Q(course_offering__section__isnull = True) | Q(course_offering__section__is_active = True),
        ).exists():
            raise ValueError(Messages.ATTENDANCE_ENROLLMENT_NOT_FOUND)

        attendance_date = self._parse_date(data["date"])
        self.validate_date(attendance_date)
        self.validate_status(data["status"])

    @staticmethod
    def validate_date(value):
        if isinstance(value,str):
            value = datetime.strptime(value,"%Y-%m-%d").date()

        if value > date.today():
            raise ValueError(Messages.ATTENDANCE_DATE_IN_FUTURE)

        return value

    @staticmethod
    def validate_status(status):
        valid_statuses = [choice[0] for choice in Attendance.Status.choices]

        if status not in valid_statuses:
            raise ValueError(Messages.ATTENDANCE_INVALID_STATUS.format(", ".join(valid_statuses)))

    @staticmethod
    def _parse_date(value):
        if isinstance(value,datetime):
            return value.date()

        if isinstance(value,date):
            return value

        try:
            return datetime.strptime(value,"%Y-%m-%d").date()

        except(TypeError,ValueError):
            raise ValueError(Messages.ATTENDANCE_DATE_INVALID_FORMAT)