from teachers.dtos.teacher_list_dto import TeacherListDTO
from teachers.dtos.teacher_reference_dto import TeacherReferenceDTO


class TeacherMapper:
    @staticmethod
    def to_list_dto(teacher):
        return TeacherListDTO(
            id = teacher.id,
            employee_id = teacher.employee_id,
            name = f"{teacher.first_name} {teacher.last_name}",
            email = teacher.email,
            designation = teacher.designation,
            department_id = teacher.department_id,
            department_name = teacher.department.name if teacher.department_id else None,
        ).to_dict()

    @staticmethod
    def to_reference_dto(teacher):
        return TeacherReferenceDTO(
            id = teacher.id,
            name = f"{teacher.first_name} {teacher.last_name}",
        ).to_dict()
