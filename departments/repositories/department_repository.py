from django.db.models import Q
from common.repositories.base_repository import BaseRepository
from departments.models import Department

#Only Name sorting is supported (by design - see common.utils.apply_ordering()).
ORDERING_FIELDS = {
    "name": ("name",),
}
DEFAULT_ORDERING = "name"


class DepartmentRepository(BaseRepository):
    def __init__(self):
        super().__init__(Department)

    def get_queryset_for_list(self, search = None):
        #Departments are not passed through apply_data_scope (they are shared data,
        #see common/permissions.py), so the soft-delete filter must be applied here.
        #Without it, deleted departments stayed visible in the admin list while
        #disappearing from every dropdown, which uses get_queryset_for_reference().
        #No .order_by() here - final ordering is applied by the service via
        #common.utils.apply_ordering() (see ORDERING_FIELDS above).
        queryset = self.model.objects.filter(is_deleted = False).only(
            "id", "name", "code", "description", "is_active",
        )

        if search:
            for term in search.split():
                queryset = queryset.filter(
                    Q(name__icontains = term)
                    | Q(code__icontains = term)
                )

        return queryset

    def get_queryset_for_reference(self, search = None):
        # Reference/dropdown use only (new-record selection) - inactive
        # departments are excluded here, unlike get_queryset_for_list() above
        # which the admin table still needs to show them in. An existing
        # record already pointing at a since-deactivated department is
        # unaffected: the edit form shows its current value via the row's own
        # department_name, not by requiring it to be present in this list.
        queryset = self.model.objects.filter(is_deleted = False, is_active = True).only(
            "id", "name",
        ).order_by("name")

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