from common.repositories.base_repository import BaseRepository
from courses.models import Course


class CourseRepository(BaseRepository):
    def __init__(self):
        super().__init__(Course)

    def code_exists(self, code, exclude_id = None):
        query = self.model.objects.filter(code__iexact = code)

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
        course.description = data.get("description", "").strip()
        course.credits = data["credits"]
        course.department_id = data["department"]
        course.teacher_id = data.get("teacher")
        course.is_active = data.get("is_active", True) in (True, "on", "true", "True")
