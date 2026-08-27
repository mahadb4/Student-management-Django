from course_offerings.dtos.course_offering_list_dto import CourseOfferingListDTO


class CourseOfferingMapper:
    @staticmethod
    def to_list_dto(offering):
        course = (
            {"id": offering.course.id, "name": offering.course.name, "code": offering.course.code}
            if offering.course_id else None
        )

        teacher = (
            {"id": offering.teacher.id, "name": f"{offering.teacher.first_name} {offering.teacher.last_name}"}
            if offering.teacher_id else None
        )

        section = (
            {"id": offering.section.id, "name": offering.section.name}
            if offering.section_id else None
        )

        return CourseOfferingListDTO(
            id=offering.id,
            semester=offering.semester,
            academic_year=offering.academic_year,
            is_active=offering.is_active,
            course=course,
            teacher=teacher,
            section=section,
        ).to_dict()
