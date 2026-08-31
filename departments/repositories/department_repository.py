from django.db.models import Q
from common.repositories.base_repository import BaseRepository
from departments.models import Department


class DepartmentRepository(BaseRepository):
    def __init__(self):
        super().__init__(Department)

    def get_queryset_for_list(self, search = None):
        queryset = self.model.objects.only(
            "id", "name", "code", "description", "is_active",
        ).order_by("id")

        if search:
            for term in search.split():
                queryset = queryset.filter(
                    Q(name__icontains = term)
                    | Q(code__icontains = term)
                )

        return queryset

    def name_exists(self, name, exclude_id = None):
        query = self.model.objects.filter(
            name__iexact = name,
            is_deleted = False,
        )

        if exclude_id is not None:
            query = query.exclude(id = exclude_id)

        return query.exists()

    def code_exists(self, code, exclude_id = None):
        query = self.model.objects.filter(
            code__iexact = code,
            is_deleted = False,
        )

        if exclude_id is not None:
            query = query.exclude(id = exclude_id)

        return query.exists()

    def create(self, data):
        department = self.model()
        self.fill(department, data)
        department.save()
        return department

    def update(self, department, data):
        self.fill(department, data)
        department.save()
        return department

    def fill(self, department, data):
        department.name = data["name"].strip()
        department.code = data["code"].strip()
        department.description = (data.get("description") or "").strip()
        department.is_active = data.get("is_active", True) in (True, "on", "true", "True")