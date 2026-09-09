from students.dtos.student_list_dto import StudentListDTO
from students.dtos.student_reference_dto import StudentReferenceDTO

class StudentMapper:
    @staticmethod
    def to_list_dto(student):
        return StudentListDTO(
            id = student.id,
            name = f"{student.effective_first_name} {student.effective_last_name}",
            student_email = student.effective_email,
            department_name = student.department.name if student.department_id else None,
            section_name = student.section.name if student.section_id else None,
        ).to_dict()

    @staticmethod
    def to_reference_dto(student):
        return StudentReferenceDTO(
            id = student.id,
            name = f"{student.effective_first_name} {student.effective_last_name}",
            student_email = student.effective_email,
            section_id = student.section_id,
        ).to_dict()
