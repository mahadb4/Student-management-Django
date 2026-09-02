from courses.dtos.course_list_dto import CourseListDTO
from courses.dtos.course_reference_dto import CourseReferenceDTO


class CourseMapper:
    @staticmethod
    def to_list_dto(course):
        return CourseListDTO(
            id = course.id,
            code = course.code,
            name = course.name,
            credits = course.credits,
            semester_number = course.semester_number,
            department_name = course.department.name if course.department_id else None,
            teacher_name = f"{course.teacher.first_name} {course.teacher.last_name}" if course.teacher_id else None,
        ).to_dict()

    @staticmethod
    def to_reference_dto(course):
        return CourseReferenceDTO(
            id = course.id,
            name = course.name,
            code = course.code,
            semester_number = course.semester_number,
            department_id = course.department_id,
            department_name = course.department.name if course.department_id else None,
        ).to_dict()
