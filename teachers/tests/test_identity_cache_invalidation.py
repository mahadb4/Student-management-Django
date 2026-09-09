from datetime import date
from django.test import TestCase
from common.cache.cache_service import CacheService
from departments.models import Department
from sections.models import Section
from teachers.cache.teacher_cache import TeacherCache
from teachers.models import Teacher
from teachers.repositories.teacher_repository import TeacherRepository
from teachers.services.teacher_service import TeacherService
from teachers.services.teacher_validator import TeacherValidator
from courses.cache.course_cache import CourseCache
from courses.mappers.course_mapper import CourseMapper
from courses.models import Course
from courses.repositories.course_repository import CourseRepository
from users.models import User


class FakeAdmin:
    is_authenticated = True
    is_superuser = True


#Identity updates must invalidate the Teacher cache.
class TeacherIdentityCacheInvalidationTests(TestCase):

    def setUp(self):
        self.department = Department.objects.create(name = "Computing", code = "CMP")
        self.cache = TeacherCache(CacheService())
        self.service = TeacherService(TeacherValidator(), TeacherRepository(), self.cache)
        self.admin = FakeAdmin()

        self.user = User.objects.create_user(
            email = "cache-teacher@example.com", name = "Before Update", password = "x", role = "teacher",
        )
        self.teacher = Teacher.objects.create(
            user = self.user, employee_id = "CACHET1", phone_number = "1234567",
            department = self.department, designation = "Lecturer", qualification = "MSc",
            gender = "M", date_of_birth = date(1980, 1, 1), date_of_joining = date(2020, 1, 1), salary = 1,
        )

    def _full_update_data(self, teacher, **overrides):
        data = {
            "first_name": teacher.effective_first_name,
            "last_name": teacher.effective_last_name,
            "employee_id": teacher.employee_id,
            "email": teacher.effective_email,
            "phone_number": teacher.phone_number,
            "department": teacher.department_id,
            "designation": teacher.designation,
            "qualification": teacher.qualification,
            "gender": teacher.gender,
            "date_of_birth": teacher.date_of_birth,
            "date_of_joining": teacher.date_of_joining,
            "salary": teacher.salary,
            "address": teacher.address,
            "is_active": teacher.is_active,
        }
        data.update(overrides)
        return data

    def test_identity_update_invalidates_detail_cache(self):
        before = self.service.get(self.teacher.id)
        self.assertEqual(before.effective_first_name, "Before")

        data = self._full_update_data(self.teacher, first_name = "After", last_name = "Update")
        self.service.update(self.teacher.id, data)

        after = self.service.get(self.teacher.id)
        self.assertEqual(after.effective_first_name, "After")

    def test_identity_update_invalidates_list_cache(self):
        self.service.get_list(self.admin, None, 1, 10, ordering = "name")

        data = self._full_update_data(self.teacher, first_name = "ListUpdated", last_name = "Name")
        self.service.update(self.teacher.id, data)

        result = self.service.get_list(self.admin, None, 1, 10, ordering = "name")
        names = [row["name"] for row in result["results"]]
        self.assertIn("ListUpdated Name", names)

    # Course list cache is not invalidated by a teacher update (pre-existing,
    # TTL-bounded behavior - see course_cache.py).
    def test_teacher_identity_update_does_not_actively_invalidate_course_list_cache(self):
        course = Course.objects.create(
            name = "Algorithms", code = "CACHECOURSE1", credits = 3,
            department = self.department, teacher = self.teacher,
        )
        course_cache = CourseCache(CacheService())
        course_repo = CourseRepository()

        # Warm Course's list cache with the OLD teacher name.
        loaded = course_repo.get_queryset_for_list().get(id = course.id)
        stale_payload = {"results": [CourseMapper.to_list_dto(loaded)]}
        course_cache.cache.set(
            course_cache.list_key(course_cache.scope_token_for(self.admin), None, 1, 10),
            stale_payload, course_cache.list_timeout,
        )

        data = self._full_update_data(self.teacher, first_name = "Renamed", last_name = "Teacher")
        self.service.update(self.teacher.id, data)

        cached = course_cache.cache.get(
            course_cache.list_key(course_cache.scope_token_for(self.admin), None, 1, 10)
        )
        self.assertEqual(cached["results"][0]["teacher_name"], "Before Update")

        # Self-heals once the cache entry expires/is cleared.
        course_cache.invalidate_lists()
        fresh = course_repo.get_queryset_for_list().get(id = course.id)
        fresh_dto = CourseMapper.to_list_dto(fresh)
        self.assertEqual(fresh_dto["teacher_name"], "Renamed Teacher")

    def test_teacher_update_does_not_invalidate_unrelated_student_namespace(self):
        from students.cache.student_cache import StudentCache
        from students.models import Student
        from sections.models import Section

        section = Section.objects.create(
            name = "A", department = self.department, semester_number = 1, academic_year = 2026,
        )
        student = Student.objects.create(
            user = User.objects.create_user(
                email = "cachestudentuntouched@example.com", name = "Untouched Student", password = "x", role = "student",
            ),
            parents_phone_number = "1234567",
            date_of_birth = date(2000, 1, 1), gender = "M",
            department = self.department, section = section,
        )
        student_cache = StudentCache(CacheService())
        student_cache.cache.set(student_cache.detail_key(student.id), {"marker": "untouched"}, None)

        data = self._full_update_data(self.teacher, first_name = "Whatever", last_name = "Name")
        self.service.update(self.teacher.id, data)

        self.assertEqual(
            student_cache.cache.get(student_cache.detail_key(student.id)),
            {"marker": "untouched"},
        )
