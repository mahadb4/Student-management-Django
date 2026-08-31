from enrollments.dtos.enrollment_list_dto import EnrollmentListDTO


class EnrollmentMapper:
    @staticmethod
    def to_list_dto(enrollment):
        course = {
            "id": enrollment.course_offering.course.id,
            "name": enrollment.course_offering.course.name,
            "code": enrollment.course_offering.course.code,
        }

        section = (
            {"id": enrollment.course_offering.section.id, "name": enrollment.course_offering.section.name}
            if enrollment.course_offering.section_id else None
        )

        course_offering = {
            "id": enrollment.course_offering.id,
            "semester": enrollment.course_offering.semester,
            "academic_year": enrollment.course_offering.academic_year,
            "course": course,
            "section": section,
        }

        student = {
            "id": enrollment.student.id,
            "name": f"{enrollment.student.first_name} {enrollment.student.last_name}",
            "student_email": enrollment.student.student_email,
        }

        return EnrollmentListDTO(
            id = enrollment.id,
            status = enrollment.status,
            student = student,
            course_offering = course_offering,
        ).to_dict()
