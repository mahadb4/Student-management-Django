from common.repositories.base_repository import BaseRepository
from attendance.models import Attendance

class AttendanceRepository(BaseRepository):
    def __init__(self):
        super().__init__(Attendance)

    def get_queryset_for_list(self):
        return self.model.objects.select_related("enrollment__student","enrollment__course_offering__course").only(
            "id","date","status","remarks","enrollment__id","enrollment__student__id",
            "enrollment__student__first_name","enrollment__student__last_name",
            "enrollment__course_offering__id","enrollment__course_offering__course__id",
            "enrollment__course_offering__course__code",
        )

    def get_by_enrollment_and_date(self,enrollment_id,attendance_date):
        return self.model.objects.filter(
            enrollment_id = enrollment_id,
            date = attendance_date,
        ).first()

    def get_by_enrollment(self,enrollment_id):
        return self.model.objects.filter(enrollment_id = enrollment_id)

    def attendance_exists(self,enrollment_id,attendance_date,exclude_id = None):
        queryset = self.model.objects.filter(
            enrollment_id = enrollment_id,
            date = attendance_date,
        )

        if exclude_id is not None:
            queryset = queryset.exclude(id = exclude_id)

        return queryset.exists()

    def create(self,data):
        attendance = self.model()
        self.fill(attendance,data)
        attendance.save()
        return attendance

    def update(self,attendance,data):
        self.fill(attendance,data)
        attendance.save()
        return attendance

    def fill(self,attendance,data):
        enrollment = data["enrollment"]
        attendance.enrollment_id = enrollment.id if hasattr(enrollment,"id") else enrollment
        attendance.date = data["date"]
        attendance.status = data["status"]
        attendance.remarks = (data.get("remarks") or "").strip()