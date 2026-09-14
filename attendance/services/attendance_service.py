from django.db import IntegrityError, transaction
from django.db.models import Q
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
        # course_offering.is_active isn't recomputed when its Course/Teacher/
        # Section is later deactivated (no cascade in this system), so it can
        # go stale relative to its parents - re-check them directly here too.
        # Section is nullable on CourseOffering, so a missing section must not
        # be excluded by the active check (Q keeps offerings with no section).
        return Enrollment.objects.select_related(
            "student",
            "course_offering",
            "course_offering__course",
            "course_offering__teacher",
            "course_offering__section",
        ).filter(
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

    # One class + one date = one logical write. Used by POST /attendance/bulk/
    # instead of the frontend looping create() once per student - see
    # attendance_api.attendance_bulk_api. teacher is None for an admin caller,
    # mirroring create()/update()'s own convention (no ownership check then).
    def create_bulk(self,course_offering_id,date_raw,records,teacher):
        from course_offerings.models import CourseOffering

        if not course_offering_id or not date_raw or not isinstance(records,list) or not records:
            raise ValueError(Messages.ATTENDANCE_BULK_PAYLOAD_INVALID)

        attendance_date = self.validator._parse_date(date_raw)
        self.validator.validate_date(attendance_date)

        try:
            course_offering = CourseOffering.objects.select_related("teacher").get(
                id = course_offering_id, is_deleted = False,
            )
        except CourseOffering.DoesNotExist:
            raise ValueError(Messages.ATTENDANCE_COURSE_OFFERING_NOT_FOUND)

        # Same ownership rule as create()/update() above - only applies to an
        # actual Teacher caller, never to teacher=None (admin).
        if teacher is not None and course_offering.teacher_id != teacher.id:
            raise ValueError(Messages.ATTENDANCE_COURSE_OFFERING_NOT_ASSIGNED)

        # The complete roster this course offering is expected to submit for -
        # same ACTIVE + not-deleted/inactive-parent checks as
        # get_active_enrollment(), just for every enrollment in the class at
        # once instead of a single lookup.
        active_enrollments = {
            enrollment.id: enrollment
            for enrollment in Enrollment.objects.select_related(
                "student","course_offering","course_offering__course",
                "course_offering__teacher","course_offering__section",
            ).filter(
                course_offering_id = course_offering.id,
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
            )
        }

        if not active_enrollments:
            raise ValueError(Messages.ATTENDANCE_NO_ACTIVE_STUDENTS)

        submitted_ids = set()

        for record in records:
            if not isinstance(record,dict) or "enrollment_id" not in record or "status" not in record:
                raise ValueError(Messages.ATTENDANCE_BULK_PAYLOAD_INVALID)

            enrollment_id = record["enrollment_id"]
            self.validator.validate_status(record["status"])

            if enrollment_id not in active_enrollments:
                raise ValueError(Messages.ATTENDANCE_ENROLLMENT_NOT_FOUND)

            submitted_ids.add(enrollment_id)

        # Reject incomplete/duplicate-in-payload submissions - one record per
        # active enrollment, no more, no less. This is the server-side backstop
        # for the same rule the frontend's Save button already enforces.
        if submitted_ids != set(active_enrollments.keys()):
            raise ValueError(Messages.ATTENDANCE_BULK_INCOMPLETE)

        if self.repository.model.objects.filter(
            enrollment_id__in = submitted_ids, date = attendance_date,
        ).exists():
            raise ValueError(Messages.ATTENDANCE_ALREADY_EXISTS.format(course_offering_id,attendance_date))

        try:
            with transaction.atomic():
                new_records = [
                    self.repository.model(
                        enrollment_id = record["enrollment_id"],
                        date = attendance_date,
                        status = record["status"],
                        remarks = (record.get("remarks") or "").strip(),
                    )
                    for record in records
                ]
                self.repository.model.objects.bulk_create(new_records)
        except IntegrityError:
            # A concurrent request created one of these rows first (the
            # unique_enrollment_date constraint is the real guard) - the whole
            # batch rolled back atomically above, nothing partially written.
            raise ValueError(Messages.ATTENDANCE_ALREADY_EXISTS.format(course_offering_id,attendance_date))

        return self.repository.model.objects.filter(
            enrollment_id__in = submitted_ids, date = attendance_date,
        ).select_related("enrollment__student__user")

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
