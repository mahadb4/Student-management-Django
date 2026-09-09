from django.db import transaction
from django.db.models import Q
from common.repositories.base_repository import BaseRepository
from common.utils import build_full_name
from teachers.models import Teacher

#Only Name sorting is supported (by design - see common.utils.apply_ordering()).
ORDERING_FIELDS = {
    "name": ("user__name",),
}
DEFAULT_ORDERING = "name"


class TeacherRepository(BaseRepository):
    def __init__(self):
        super().__init__(Teacher)

    def get(self, object_id):
        return self.model.objects.select_related("user").get(
            id = object_id, is_deleted = False,
        )

    def get_queryset_for_list(self, search = None, department_id = None):
        #No .order_by() here - final ordering is applied by the service, after
        #apply_data_scope(), via common.utils.apply_ordering() (see ORDERING_FIELDS above).
        queryset = self.model.objects.select_related("department", "user").only(
            "id", "employee_id", "designation",
            "user_id", "user__name", "user__email",
            "department__id", "department__name",
        )

        if search:
            for term in search.split():
                queryset = queryset.filter(
                    Q(employee_id__icontains = term)
                    | Q(designation__icontains = term)
                    | Q(user__name__icontains = term)
                    | Q(user__email__icontains = term)
                )

        if department_id is not None:
            queryset = queryset.filter(department_id = department_id)

        return queryset

    def get_queryset_for_reference(self, department_id = None):
        # Reference/dropdown use only (new-record selection) - see
        # DepartmentRepository.get_queryset_for_reference for why is_active is
        # filtered here but not in get_queryset_for_list().
        queryset = self.model.objects.select_related("user").filter(
            is_deleted = False, is_active = True,
        ).only(
            "id", "department_id", "user_id", "user__name", "user__email",
        ).order_by("user__name")

        if department_id is not None:
            queryset = queryset.filter(department_id = department_id)

        return queryset

    def employee_id_exists(self, employee_id, exclude_id = None):
        query = self.model.objects.filter(
            employee_id = employee_id,
            is_deleted = False,
        )

        if exclude_id is not None:
            query = query.exclude(id = exclude_id)

        return query.exists()

    def create(self, data, user):
        teacher = self.model(user = user)
        self.fill(teacher, data)
        teacher.save()
        return teacher

    def update(self, teacher, data):
        with transaction.atomic():
            self.fill(teacher, data)
            teacher.save()
        return teacher

    def fill(self, teacher, data):
        first_name = data["first_name"].strip()
        last_name = data["last_name"].strip()
        email = data["email"].strip()

        full_name = build_full_name(first_name, last_name)
        user = teacher.user
        if user.name != full_name or user.email != email:
            user.name = full_name
            user.email = email
            user.save(update_fields = ["name", "email"])

        teacher.employee_id = data["employee_id"].strip()
        teacher.phone_number = data["phone_number"].strip()
        teacher.department_id = data["department"]
        teacher.designation = data["designation"].strip()
        teacher.qualification = data["qualification"].strip()
        teacher.gender = data["gender"]
        teacher.date_of_birth = data["date_of_birth"]
        teacher.date_of_joining = data["date_of_joining"]
        teacher.salary = data["salary"]
        teacher.address = (data.get("address") or "").strip()
        teacher.is_active = data.get("is_active", True) in (True, "on", "true", "True")
