from course_offerings.dtos.course_offering_list_dto import CourseOfferingListDTO
from course_offerings.dtos.course_offering_reference_dto import CourseOfferingReferenceDTO
from course_offerings.dtos.course_offering_teacher_list_dto import CourseOfferingTeacherListDTO


class CourseOfferingMapper:
    @staticmethod
    def to_list_dto(offering):
        course_id = offering.course.id if offering.course_id else None
        course_name = offering.course.name if offering.course_id else None
        course_code = offering.course.code if offering.course_id else None

        teacher_id = offering.teacher.id if offering.teacher_id else None
        teacher_name = (
            f"{offering.teacher.first_name} {offering.teacher.last_name}"
            if offering.teacher_id else None
        )

        section_id = offering.section.id if offering.section_id else None
        section_name = offering.section.name if offering.section_id else None

        return CourseOfferingListDTO(
            id = offering.id,
            semester = offering.semester,
            academic_year = offering.academic_year,
            is_active = offering.is_active,
            course_id = course_id,
            course_name = course_name,
            course_code = course_code,
            teacher_id = teacher_id,
            teacher_name = teacher_name,
            section_id = section_id,
            section_name = section_name,
        ).to_dict()

    # Read-only projection for consumers that only display an offering (no
    # edit form needing raw FK ids) - e.g. the Student My Courses "browse to
    # enroll" tab and Teacher's read-only offering lookups.
    @staticmethod
    def to_reference_dto(offering):
        course_name = offering.course.name if offering.course_id else None
        course_code = offering.course.code if offering.course_id else None

        teacher_name = (
            f"{offering.teacher.first_name} {offering.teacher.last_name}"
            if offering.teacher_id else None
        )

        section_name = offering.section.name if offering.section_id else None

        return CourseOfferingReferenceDTO(
            id = offering.id,
            semester = offering.semester,
            academic_year = offering.academic_year,
            is_active = offering.is_active,
            course_name = course_name,
            course_code = course_code,
            teacher_name = teacher_name,
            section_name = section_name,
        ).to_dict()

    # "My Classes" (Teacher's own offerings) - no teacher_name (it's their
    # own), no raw ids, plus enrolled_students_count computed by the
    # repository's annotation rather than the frontend downloading every
    # enrollment row to count them.
    @staticmethod
    def to_teacher_list_dto(offering):
        course_name = offering.course.name if offering.course_id else None
        course_code = offering.course.code if offering.course_id else None
        section_name = offering.section.name if offering.section_id else None

        return CourseOfferingTeacherListDTO(
            id = offering.id,
            course_name = course_name,
            course_code = course_code,
            semester = offering.semester,
            academic_year = offering.academic_year,
            section_name = section_name,
            is_active = offering.is_active,
            enrolled_students_count = offering.enrolled_students_count,
        ).to_dict()
