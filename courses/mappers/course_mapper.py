from courses.dtos.course_list_dto import CourseListDTO


class CourseMapper:
    @staticmethod
    def to_list_dto(course):
        department = (
            {"name": course.department.name}
            if course.department_id else None
        )

        teacher = (
            {"name": f"{course.teacher.first_name} {course.teacher.last_name}"}
            if course.teacher_id else None
        )

        return CourseListDTO(
            id = course.id,
            code = course.code,
            name = course.name,
            credits = course.credits,
            department = department,
            teacher = teacher,
        ).to_dict()
