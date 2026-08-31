from sections.dtos.section_list_dto import SectionListDTO


class SectionMapper:
    @staticmethod
    def to_list_dto(section):
        department = (
            {"id": section.department.id, "name": section.department.name}
            if section.department_id else None
        )

        return SectionListDTO(
            id = section.id,
            name = section.name,
            semester_number = section.semester_number,
            academic_year = section.academic_year,
            is_active = section.is_active,
            department = department,
        ).to_dict()
