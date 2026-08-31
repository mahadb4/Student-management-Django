from departments.dtos.department_list_dto import DepartmentListDTO


class DepartmentMapper:
    @staticmethod
    def to_list_dto(department):
        return DepartmentListDTO(
            id = department.id,
            name = department.name,
            code = department.code,
            description = department.description,
            is_active = department.is_active,
        ).to_dict()
