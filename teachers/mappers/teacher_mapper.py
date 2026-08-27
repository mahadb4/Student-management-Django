from teachers.dtos.teacher_list_dto import TeacherListDTO


class TeacherMapper:
    @staticmethod
    def to_list_dto(teacher):
        department = (
            {"name": teacher.department.name}
            if teacher.department_id else None
        )

        return TeacherListDTO(
            id=teacher.id,
            employee_id=teacher.employee_id,
            name=f"{teacher.first_name} {teacher.last_name}",
            email=teacher.email,
            designation=teacher.designation,
            department=department,
        ).to_dict()
