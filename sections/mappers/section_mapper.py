from sections.dtos.section_list_dto import SectionListDTO
from sections.dtos.section_reference_dto import SectionReferenceDTO


class SectionMapper:
    @staticmethod
    def to_list_dto(section):
        return SectionListDTO(
            id = section.id,
            name = section.name,
            semester_number = section.semester_number,
            academic_year = section.academic_year,
            is_active = section.is_active,
            department_id = section.department_id,
            department_name = section.department.name if section.department_id else None,
        ).to_dict()

    @staticmethod
    def to_reference_dto(section):
        return SectionReferenceDTO(
            id = section.id,
            name = section.name,
            semester_number = section.semester_number,
            department_name = section.department.name if section.department_id else None,
        ).to_dict()
