from common.messages import Messages
from enrollments.models import Enrollment

class AttendanceService:
    def __init__(self,validator,repository):
        self.validator = validator
        self.repository = repository

    def get(self,attendance_id):
        return self.repository.get(attendance_id)

    def get_all(self):
        return self.repository.get_all()

    def get_active_enrollment(self,enrollment_id):
        return Enrollment.objects.select_related(
            "student",
            "course_offering",
            "course_offering__teacher",
        ).filter(
            id = enrollment_id,
            status = Enrollment.Status.ACTIVE,
            is_deleted = False,
            student__is_deleted = False,
            student__is_active = True,
            course_offering__is_deleted = False,
            course_offering__is_active = True,
        ).first()

    def create(self,data,teacher):
        self.validator.validate(data)

        enrollment_id = data["enrollment_id"]
        attendance_date = self.validator._parse_date(data["date"])
        enrollment = self.get_active_enrollment(enrollment_id)

        if not enrollment:
            raise ValueError(Messages.ATTENDANCE_ENROLLMENT_NOT_FOUND)

        if enrollment.course_offering.teacher_id != teacher.id:
            raise ValueError(Messages.ATTENDANCE_COURSE_OFFERING_NOT_ASSIGNED)

        if self.repository.attendance_exists(enrollment_id,attendance_date):
            raise ValueError(Messages.ATTENDANCE_ALREADY_EXISTS.format(enrollment_id,attendance_date))

        data["enrollment"] = enrollment
        data["date"] = attendance_date
        data.pop("enrollment_id",None)

        return self.repository.create(data)

    def update(self,attendance_id,data,teacher,partial = False):
        attendance = self.repository.get(attendance_id)

        if partial:
            data = self._merge_data(attendance,data)

        self.validator.validate(data)

        enrollment_id = data["enrollment_id"]
        attendance_date = self.validator._parse_date(data["date"])
        enrollment = self.get_active_enrollment(enrollment_id)

        if not enrollment:
            raise ValueError(Messages.ATTENDANCE_ENROLLMENT_NOT_FOUND)

        if enrollment.course_offering.teacher_id != teacher.id:
            raise ValueError(Messages.ATTENDANCE_COURSE_OFFERING_NOT_ASSIGNED)

        if self.repository.attendance_exists(enrollment_id,attendance_date,attendance_id):
            raise ValueError(Messages.ATTENDANCE_ALREADY_EXISTS.format(enrollment_id,attendance_date))

        data["enrollment"] = enrollment
        data["date"] = attendance_date
        data.pop("enrollment_id",None)

        return self.repository.update(attendance,data)

    def delete(self,attendance_id):
        self.repository.delete(attendance_id)

    def mark_bulk(self,attendance_data,teacher):
        records = []

        for data in attendance_data:
            records.append(self.create(data,teacher))

        return records

    def get_enrollment_attendance(self,enrollment_id):
        return self.repository.get_by_enrollment(enrollment_id)

    def _merge_data(self,attendance,data):
        return {
            "enrollment_id":data.get("enrollment_id",attendance.enrollment_id),
            "date":data.get("date",attendance.date.isoformat()),
            "status":data.get("status",attendance.status),
            "remarks":data.get("remarks",attendance.remarks),
        }
