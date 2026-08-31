from django.db.models import Q
from common.repositories.base_repository import BaseRepository
from sections.models import Section


class SectionRepository(BaseRepository):
    def __init__(self):
        super().__init__(Section)

    def get_queryset_for_list(self, search = None):
        queryset = self.model.objects.select_related("department").only(
            "id", "name", "semester_number", "academic_year", "is_active",
            "department__id", "department__name",
        ).filter(is_deleted = False).order_by("id")

        if search:
            for term in search.split():
                queryset = queryset.filter(
                    Q(name__icontains = term)
                    | Q(department__name__icontains = term)
                )

        return queryset

    def section_exists(self, name, department_id, semester_number, academic_year, exclude_id = None):
        query = self.model.objects.filter(
            name__iexact = name,
            department_id = department_id,
            semester_number = semester_number,
            academic_year = academic_year,
            is_deleted = False,
        )

        if exclude_id is not None:
            query = query.exclude(id = exclude_id)

        return query.exists()

    def create(self, data):
        section = self.model()
        self.fill(section, data)
        section.save()
        return section

    def update(self, section, data):
        self.fill(section, data)
        section.save()
        return section

    def fill(self, section, data):
        section.name = data["name"].strip()
        section.department_id = data["department"]
        section.semester_number = data["semester_number"]
        section.academic_year = data["academic_year"]
        section.is_active = data.get("is_active", True) in (True, "on", "true", "True")
