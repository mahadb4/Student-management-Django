from common.repositories.base_repository import BaseRepository
from attendance.models import Attendance


class AttendanceRepository(BaseRepository):
    def __init__(self):
        super().__init__(Attendance)

    def attendance_exists(self, enrollment, attendance_date, exclude_id = None):
        enrollment_id = enrollment.id if hasattr(enrollment, "id") else enrollment
        query = self.model.objects.filter(enrollment_id = enrollment_id, date = attendance_date)

        if exclude_id is not None:
            query = query.exclude(id = exclude_id)

        return query.exists()

    def create(self, data):
        attendance = self.model()
        self.fill(attendance, data)
        attendance.save()
        return attendance

    def update(self, attendance, data):
        self.fill(attendance, data)
        attendance.save()
        return attendance

    def fill(self, attendance, data):
        enrollment = data["enrollment"]
        attendance.enrollment_id = enrollment.id if hasattr(enrollment, "id") else enrollment
        attendance.date = data["date"]
        attendance.status = data["status"]
        attendance.remarks = (data.get("remarks") or "").strip()
