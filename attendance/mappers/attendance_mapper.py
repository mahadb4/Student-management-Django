from attendance.dtos.attendance_list_dto import AttendanceListDTO


class AttendanceMapper:
    @staticmethod
    def to_list_dto(attendance):
        enrollment = (
            {
                "id": attendance.enrollment.id,
                "student": {
                    # "id": attendance.enrollment.student.id,
                    "name": f"{attendance.enrollment.student.first_name} {attendance.enrollment.student.last_name}",
                },
                "course": {
                    # "id": attendance.enrollment.course_offering.course.id,
                    "code": attendance.enrollment.course_offering.course.code,
                },
            }
            if attendance.enrollment_id else None
        )

        return AttendanceListDTO(
            id = attendance.id,
            date = attendance.date,
            status = attendance.status,
            remarks = attendance.remarks,
            enrollment = enrollment,
        ).to_dict()
