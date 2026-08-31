from departments.dtos.department_list_dto import DepartmentListDTO
from departments.dtos.department_reference_dto import DepartmentReferenceDTO


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

    @staticmethod
    def to_reference_dto(department):
        return DepartmentReferenceDTO(
            id = department.id,
            name = department.name,
        ).to_dict()
