from enrollments.dtos.enrollment_list_dto import EnrollmentListDTO
from enrollments.dtos.student_enrollment_list_dto import StudentEnrollmentListDTO
from enrollments.dtos.enrollment_reference_dto import EnrollmentReferenceDTO
from enrollments.dtos.enrollment_teacher_list_dto import EnrollmentTeacherListDTO


class EnrollmentMapper:
    @staticmethod
    def to_list_dto(enrollment):
        section_name = (
            enrollment.course_offering.section.name
            if enrollment.course_offering.section_id else None
        )

        return EnrollmentListDTO(
            id = enrollment.id,
            status = enrollment.status,
            student_id = enrollment.student.id,
            student_name = f"{enrollment.student.first_name} {enrollment.student.last_name}",
            student_email = enrollment.student.student_email,
            course_offering_id = enrollment.course_offering.id,
            semester = enrollment.course_offering.semester,
            academic_year = enrollment.course_offering.academic_year,
            course_name = enrollment.course_offering.course.name,
            course_code = enrollment.course_offering.course.code,
            section_name = section_name,
        ).to_dict()

    # Used only by the authenticated Student's own /students/me/courses/ -
    # drops student_id/student_name/student_email (redundant echoes of the
    # caller's own identity) and adds teacher_name (resolved from the
    # enrollment's own course_offering) so the Student My Courses UI doesn't
    # need a separate course_offerings fetch just to show who teaches each
    # of the student's own enrolled courses.
    @staticmethod
    def to_student_list_dto(enrollment):
        section_name = (
            enrollment.course_offering.section.name
            if enrollment.course_offering.section_id else None
        )

        teacher_name = (
            f"{enrollment.course_offering.teacher.first_name} {enrollment.course_offering.teacher.last_name}"
            if enrollment.course_offering.teacher_id else None
        )

        return StudentEnrollmentListDTO(
            id = enrollment.id,
            status = enrollment.status,
            course_offering_id = enrollment.course_offering.id,
            semester = enrollment.course_offering.semester,
            academic_year = enrollment.course_offering.academic_year,
            course_name = enrollment.course_offering.course.name,
            course_code = enrollment.course_offering.course.code,
            teacher_name = teacher_name,
            section_name = section_name,
        ).to_dict()

    # Used only by the Student Attendance course filter dropdown - the
    # dropdown's option value/key is the enrollment id (matched against
    # attendance rows' enrollment_id), and its label is course_name/course_code;
    # nothing else from the enrollment is rendered there.
    @staticmethod
    def to_reference_dto(enrollment):
        return EnrollmentReferenceDTO(
            id = enrollment.id,
            course_code = enrollment.course_offering.course.code,
            course_name = enrollment.course_offering.course.name,
        ).to_dict()

    # Used only by the authenticated Teacher's own /teachers/me/students/ -
    # drops the teacher's own identity (already known: it's them) and any
    # raw ids besides course_offering_id, which the Students/Attendance
    # pages' class filter dropdown needs to match rows against.
    @staticmethod
    def to_teacher_list_dto(enrollment):
        section_name = (
            enrollment.course_offering.section.name
            if enrollment.course_offering.section_id else None
        )

        return EnrollmentTeacherListDTO(
            enrollment_id = enrollment.id,
            course_offering_id = enrollment.course_offering.id,
            student_name = f"{enrollment.student.first_name} {enrollment.student.last_name}",
            student_email = enrollment.student.student_email,
            course_name = enrollment.course_offering.course.name,
            course_code = enrollment.course_offering.course.code,
            section_name = section_name,
            status = enrollment.status,
        ).to_dict()
