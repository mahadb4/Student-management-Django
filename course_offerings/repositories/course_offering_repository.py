from django.db.models import Q
from common.repositories.base_repository import BaseRepository
from course_offerings.models import CourseOffering

class CourseOfferingRepository(BaseRepository):
    def __init__(self):
        super().__init__(CourseOffering)

    def get_queryset_for_list(self, search = None):
        queryset = self.model.objects.select_related("course", "teacher", "section").only(
            "id", "semester", "academic_year", "is_active",
            "course__id", "course__name", "course__code",
            "teacher__id", "teacher__first_name", "teacher__last_name",
            "section__id", "section__name",
        ).order_by("id")

        if search:
            for term in search.split():
                queryset = queryset.filter(
                    Q(course__name__icontains = term)
                    | Q(course__code__icontains = term)
                    | Q(teacher__first_name__icontains = term)
                    | Q(teacher__last_name__icontains = term)
                    | Q(section__name__icontains = term)
                )

        return queryset

    def course_offering_exists(self,course_id,teacher_id,semester,academic_year,section_id,exclude_id = None):
        query = self.model.objects.filter(
            course_id = course_id,
            teacher_id = teacher_id,
            semester = semester,
            academic_year = academic_year,
            section_id = section_id,
            is_deleted = False,
        )

        if exclude_id is not None:
            query = query.exclude(id = exclude_id)

        return query.exists()

    def create(self,data):
        offering = self.model()
        self.fill(offering,data)
        offering.save()
        return offering

    def update(self,offering,data):
        self.fill(offering,data)
        offering.save()
        return offering

    def fill(self,offering,data):
        offering.course_id = data["course"]
        offering.teacher_id = data["teacher"]
        offering.semester = data["semester"]
        offering.academic_year = data["academic_year"]
        offering.section_id = data["section"]
        offering.is_active = data.get("is_active",True) in (True,"on","true","True")