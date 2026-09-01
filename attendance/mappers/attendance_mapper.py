from attendance.dtos.attendance_list_dto import AttendanceListDTO
from attendance.dtos.student_attendance_list_dto import StudentAttendanceListDTO
from attendance.dtos.attendance_teacher_list_dto import AttendanceTeacherListDTO


class AttendanceMapper:
    # Used by the generic Admin-facing /attendance/ list (attendance_api) -
    # Student and Teacher each have their own narrower to_*_list_dto below.
    @staticmethod
    def to_list_dto(attendance):
        has_enrollment = attendance.enrollment_id is not None

        return AttendanceListDTO(
            id = attendance.id,
            date = attendance.date,
            status = attendance.status,
            remarks = attendance.remarks,
            enrollment_id = attendance.enrollment_id if has_enrollment else None,
            student_id = attendance.enrollment.student.id if has_enrollment else None,
            student_name = f"{attendance.enrollment.student.first_name} {attendance.enrollment.student.last_name}" if has_enrollment else None,
            course_id = attendance.enrollment.course_offering.course.id if has_enrollment else None,
            course_code = attendance.enrollment.course_offering.course.code if has_enrollment else None,
        ).to_dict()

    # Used only by the authenticated Student's own /students/me/attendance/ -
    # the caller's own student_id/student_name and course_id are redundant
    # (it's already their own data), unlike the Teacher-facing to_list_dto
    # above which needs student_name to identify whose row it is.
    @staticmethod
    def to_student_list_dto(attendance):
        has_enrollment = attendance.enrollment_id is not None

        return StudentAttendanceListDTO(
            id = attendance.id,
            date = attendance.date,
            status = attendance.status,
            remarks = attendance.remarks,
            enrollment_id = attendance.enrollment_id if has_enrollment else None,
            course_code = attendance.enrollment.course_offering.course.code if has_enrollment else None,
        ).to_dict()

    # Used only by the authenticated Teacher's own /teachers/me/attendance/ -
    # drops student_id/course_id (unused by the Attendance table), keeps
    # enrollment_id (needed for the class filter) and student_name (the row
    # identifies which of the teacher's students it belongs to).
    @staticmethod
    def to_teacher_list_dto(attendance):
        has_enrollment = attendance.enrollment_id is not None

        return AttendanceTeacherListDTO(
            id = attendance.id,
            date = attendance.date,
            status = attendance.status,
            remarks = attendance.remarks,
            enrollment_id = attendance.enrollment_id if has_enrollment else None,
            student_name = f"{attendance.enrollment.student.first_name} {attendance.enrollment.student.last_name}" if has_enrollment else None,
        ).to_dict()
