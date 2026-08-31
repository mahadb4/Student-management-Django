from attendance.dtos.attendance_list_dto import AttendanceListDTO


class AttendanceMapper:
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
