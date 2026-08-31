from students.dtos.student_list_dto import StudentListDTO

class StudentMapper:
    @staticmethod
    def to_list_dto(student):
        department = (
            {"name": student.department.name}
            if student.department_id else None
        )

        section = (
            {"name": student.section.name}
            if student.section_id else None
        )

        return StudentListDTO(
            id = student.id,
            name = f"{student.first_name} {student.last_name}",
            student_email = student.student_email,
            is_active = student.is_active,
            department = department,
            section = section,
        ).to_dict()
