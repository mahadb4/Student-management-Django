from django.db.models import Q
from common.repositories.base_repository import BaseRepository
from courses.models import Course


class CourseRepository(BaseRepository):
    def __init__(self):
        super().__init__(Course)

    def get_queryset_for_list(self, search = None):
        queryset = self.model.objects.select_related("department", "teacher").only(
            "id", "code", "name", "credits",
            "department__id", "department__name",
            "teacher__id", "teacher__first_name", "teacher__last_name",
        ).order_by("id")

        if search:
            for term in search.split():
                queryset = queryset.filter(
                    Q(name__icontains = term)
                    | Q(code__icontains = term)
                    | Q(department__name__icontains = term)
                )

        return queryset

    def get_queryset_for_reference(self, department_id = None):
        queryset = self.model.objects.select_related("department").only(
            "id", "name", "code", "department_id", "department__name",
        ).order_by("name")

        if department_id is not None:
            queryset = queryset.filter(department_id = department_id)

        return queryset

    def code_exists(self, code, exclude_id = None):
        query = self.model.objects.filter(
            code__iexact = code,
        )

        if exclude_id is not None:
            query = query.exclude(id = exclude_id)

        return query.exists()

    def create(self, data):
        course = self.model()
        self.fill(course, data)
        course.save()
        return course

    def update(self, course, data):
        self.fill(course, data)
        course.save()
        return course

    def fill(self, course, data):
        course.name = data["name"].strip()
        course.code = data["code"].strip()
        course.description = (data.get("description") or "").strip()
        course.credits = data["credits"]
        course.department_id = data["department"]
        course.teacher_id = data.get("teacher")
        course.is_active = data.get("is_active", True) in (True, "on", "true", "True")