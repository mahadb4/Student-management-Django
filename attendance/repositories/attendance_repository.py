from common.repositories.base_repository import BaseRepository
from attendance.models import Attendance

class AttendanceRepository(BaseRepository):
    def __init__(self):
        super().__init__(Attendance)

    def get_queryset_for_list(self):
        #Alphabetical by student name - same ordering the Teacher Attendance
        #register uses for its class roster (EnrollmentRepository's
        #DEFAULT_ORDERING = "name", i.e. student__user__name), so the Admin
        #Attendance page's per-class/per-date view reads as the same class
        #list a teacher would see, not an arbitrary attendance-record order.
        #-date/-id remain as tiebreakers for same-name rows (e.g. once this
        #queryset spans more than one date/session).
        return self.model.objects.select_related(
            "enrollment__student__user","enrollment__course_offering__course",
        ).only(
            "id","date","status","remarks","enrollment__id","enrollment__student__id",
            "enrollment__student__user_id","enrollment__student__user__name",
            "enrollment__student__user__email",
            "enrollment__course_offering__id","enrollment__course_offering__course__id",
            "enrollment__course_offering__course__code",
        ).order_by("enrollment__student__user__name","-date","-id")

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