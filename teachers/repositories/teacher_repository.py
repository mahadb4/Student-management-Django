from django.db.models import Q
from common.repositories.base_repository import BaseRepository
from teachers.models import Teacher


class TeacherRepository(BaseRepository):
    def __init__(self):
        super().__init__(Teacher)

    def get_queryset_for_list(self, search = None):
        queryset = self.model.objects.select_related("department").only(
            "id", "employee_id", "first_name", "last_name", "email", "designation",
            "department__id", "department__name",
        ).order_by("id")

        if search:
            for term in search.split():
                queryset = queryset.filter(
                    Q(first_name__icontains = term)
                    | Q(last_name__icontains = term)
                    | Q(email__icontains = term)
                    | Q(employee_id__icontains = term)
                    | Q(designation__icontains = term)
                )

        return queryset

    def get_queryset_for_reference(self, department_id = None):
        queryset = self.model.objects.filter(is_deleted = False).only(
            "id", "first_name", "last_name", "department_id",
        ).order_by("first_name", "last_name")

        if department_id is not None:
            queryset = queryset.filter(department_id = department_id)

        return queryset

    def email_exists(self, email, exclude_id = None):
        query = self.model.objects.filter(
            email__iexact = email,
            is_deleted = False,
        )

        if exclude_id is not None:
            query = query.exclude(id = exclude_id)

        return query.exists()

    def employee_id_exists(self, employee_id, exclude_id = None):
        query = self.model.objects.filter(
            employee_id = employee_id,
            is_deleted = False,
        )

        if exclude_id is not None:
            query = query.exclude(id = exclude_id)

        return query.exists()

    def create(self, data):
        teacher = self.model()
        self.fill(teacher, data)
        teacher.save()
        return teacher

    def update(self, teacher, data):
        self.fill(teacher, data)
        teacher.save()
        return teacher

    def fill(self, teacher, data):
        teacher.first_name = data["first_name"].strip()
        teacher.last_name = data["last_name"].strip()
        teacher.employee_id = data["employee_id"].strip()
        teacher.email = data["email"].strip()
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