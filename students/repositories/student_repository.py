from django.db import transaction
from django.db.models import Q
from common.repositories.base_repository import BaseRepository
from common.utils import build_full_name
from students.models import Student

#Only Name sorting is supported (by design - see common.utils.apply_ordering()).
ORDERING_FIELDS = {
    "name": ("user__name",),
}
DEFAULT_ORDERING = "name"


class StudentRepository(BaseRepository):
    def __init__(self):
        super().__init__(Student)

    def get(self, object_id):
        return self.model.objects.select_related("user").get(
            id = object_id, is_deleted = False,
        )

    def get_queryset_for_list(self, search = None, department_id = None):
        #No .order_by() here - final ordering is applied by the service, after
        #apply_data_scope(), via common.utils.apply_ordering() (see ORDERING_FIELDS
        #above). Search/filtering stays here, unchanged.
        queryset = self.model.objects.select_related(
            "department", "section", "user").only(

            "id", "is_active",
            "user_id", "user__name", "user__email", "user__date_of_birth",
            "user__gender", "user__address", "user__profile_picture_key",
            "department__id", "department__name",
            "section__id", "section__name",

        )

        if search:
            for term in search.split():
                queryset = queryset.filter(
                    Q(user__name__icontains = term)
                    | Q(user__email__icontains = term)
                )

        if department_id is not None:
            queryset = queryset.filter(department_id = department_id)

        return queryset

    def get_queryset_for_reference(self):
        # Reference/dropdown use only (new-record selection, e.g. the Admin
        # Enrollment form's Student picker) - see
        # DepartmentRepository.get_queryset_for_reference for why is_active is
        # filtered here but not in get_queryset_for_list().
        return self.model.objects.select_related("user").filter(
            is_deleted = False, is_active = True,
        ).only(
            "id", "section_id", "user_id", "user__name", "user__email",
        ).order_by("user__name")

    def create(self, data, user):
        student = self.model(user = user)
        self.fill(student, data)
        student.save()
        return student

    def update(self, student, data):
        with transaction.atomic():
            self.fill(student, data)
            student.save()
        return student

    def update_profile_picture_key(self, student, key):
        user = student.user
        user.profile_picture_key = key
        user.save(update_fields = ["profile_picture_key", "updated_at"])

    def fill(self, student, data):
        first_name = data["first_name"].strip()
        last_name = data["last_name"].strip()
        email = data["student_email"].strip()

        full_name = build_full_name(first_name, last_name)
        user = student.user
        user.name = full_name
        user.email = email
        user.date_of_birth = data["date_of_birth"]
        user.gender = data["gender"]
        user.address = (data.get("address") or "").strip()
        user.save(update_fields = ["name", "email", "date_of_birth", "gender", "address"])

        student.parents_phone_number = data["parents_phone_number"].strip()
        student.department_id = data.get("department")
        student.section_id = data.get("section")
        student.is_active = data.get(
            "is_active", True) in (True, "on", "true", "True")
