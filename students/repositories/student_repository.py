from django.db.models import Q
from common.repositories.base_repository import BaseRepository
from students.models import Student

#Only Name sorting is supported (by design - see common.utils.apply_ordering()).
#"name" isn't a real DB column (StudentListDTO computes it from first/last), so
#it maps to the actual underlying fields here.
ORDERING_FIELDS = {
    "name": ("first_name", "last_name"),
}
DEFAULT_ORDERING = "name"


class StudentRepository(BaseRepository):
    def __init__(self):
        super().__init__(Student)

    def get_queryset_for_list(self, search = None, department_id = None):
        #No .order_by() here - final ordering is applied by the service, after
        #apply_data_scope(), via common.utils.apply_ordering() (see ORDERING_FIELDS
        #above). Search/filtering stays here, unchanged.
        queryset = self.model.objects.select_related(
            "department", "section").only(

            "id", "first_name", "last_name", "student_email", "is_active",
            "department__id", "department__name",
            "section__id", "section__name",

        )

        if search:
            for term in search.split():
                queryset = queryset.filter(
                    Q(first_name__icontains = term)
                    | Q(last_name__icontains = term)
                    | Q(student_email__icontains = term)
                )

        if department_id is not None:
            queryset = queryset.filter(department_id = department_id)

        return queryset

    def get_queryset_for_reference(self):
        # Reference/dropdown use only (new-record selection, e.g. the Admin
        # Enrollment form's Student picker) - see
        # DepartmentRepository.get_queryset_for_reference for why is_active is
        # filtered here but not in get_queryset_for_list().
        return self.model.objects.filter(is_deleted = False, is_active = True).only(
            "id", "first_name", "last_name", "student_email", "section_id",
        ).order_by("first_name", "last_name")

    def email_exists(self, email, exclude_id = None):
        query = self.model.objects.filter(
            student_email__iexact = email,
            is_deleted = False,
        )

        if exclude_id is not None:
            query = query.exclude(id = exclude_id)

        return query.exists()

    def create(self, data):
        student = self.model()
        self.fill(student, data)
        student.save()
        return student

    def update(self, student, data):
        self.fill(student, data)
        student.save()
        return student

    def fill(self, student, data):
        student.first_name = data["first_name"].strip()
        student.last_name = data["last_name"].strip()
        student.student_email = data["student_email"].strip()
        student.parents_phone_number = data["parents_phone_number"].strip()
        student.date_of_birth = data["date_of_birth"]
        student.gender = data["gender"]
        student.address = (data.get("address") or "").strip()
        student.department_id = data.get("department")
        student.section_id = data.get("section")
        student.is_active = data.get(
            "is_active", True) in (True, "on", "true", "True")