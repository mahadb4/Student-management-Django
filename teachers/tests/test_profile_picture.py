from datetime import date
from django.core.exceptions import ObjectDoesNotExist
from django.test import TestCase
from common.cache.cache_service import CacheService
from common.permissions import apply_data_scope
from courses.models import Course
from course_offerings.models import CourseOffering
from departments.models import Department
from enrollments.models import Enrollment
from sections.models import Section
from students.models import Student
from teachers.cache.teacher_cache import TeacherCache
from teachers.models import Teacher
from teachers.repositories.teacher_repository import TeacherRepository
from teachers.services.teacher_service import TeacherService
from teachers.services.teacher_validator import TeacherValidator
from users.models import User


#Hand-written in-memory fake of S3Service's public surface - no real AWS calls,
#matching this repo's existing stub/fake test convention.
class FakeS3Service:

    def __init__(self):
        self.objects = {}
        self.deleted_keys = []

    def generate_upload_url(self, key, content_type, expires_in = 300):
        return f"https://fake-s3/upload/{key}?ct={content_type}&expires={expires_in}"

    def generate_view_url(self, key, expires_in = 300):
        return f"https://fake-s3/view/{key}?expires={expires_in}"

    def object_exists(self, key):
        return key in self.objects

    def head_object(self, key):
        if key not in self.objects:
            return None
        return {"content_length": self.objects[key], "content_type": "image/jpeg"}

    def delete_object(self, key):
        self.objects.pop(key, None)
        self.deleted_keys.append(key)

    def put(self, key, content_length = 1024):
        self.objects[key] = content_length


class ProfilePictureServiceTestBase(TestCase):

    def setUp(self):
        self.department = Department.objects.create(name = "Computing", code = "CMP")
        self.repository = TeacherRepository()
        self.service = TeacherService(TeacherValidator(), self.repository, TeacherCache(CacheService()))
        self.s3 = FakeS3Service()

        self.teacher = self._make_teacher("t1@example.com", "T1", "Teacher One")
        self.other_teacher = self._make_teacher("t2@example.com", "T2", "Teacher Two")

    def _make_teacher(self, email, employee_id, name):
        user = User.objects.create_user(email = email, name = name, password = "x", role = "teacher")
        return Teacher.objects.create(
            user = user, employee_id = employee_id, phone_number = "123",
            department = self.department, designation = "Prof", qualification = "PhD",
            salary = 1000,
        )


class GenerateUploadUrlTests(ProfilePictureServiceTestBase):

    def test_generates_backend_derived_key_and_url(self):
        result = self.service.generate_profile_picture_upload_url(self.teacher.id, "image/png", self.s3)

        self.assertEqual(result["key"], f"teachers/{self.teacher.id}/profile.png")
        self.assertIn(result["key"], result["upload_url"])

    def test_rejects_unsupported_content_type(self):
        with self.assertRaises(ValueError):
            self.service.generate_profile_picture_upload_url(self.teacher.id, "text/plain", self.s3)

    def test_raises_for_unknown_teacher(self):
        with self.assertRaises(Teacher.DoesNotExist):
            self.service.generate_profile_picture_upload_url(999999, "image/jpeg", self.s3)


class ConfirmUploadTests(ProfilePictureServiceTestBase):

    def test_confirm_fails_when_object_does_not_exist_in_s3(self):
        key = f"teachers/{self.teacher.id}/profile.jpg"
        with self.assertRaises(ValueError):
            self.service.confirm_profile_picture_upload(self.teacher.id, key, self.s3)

        self.teacher.refresh_from_db()
        self.assertIsNone(self.teacher.user.profile_picture_key)

    def test_confirm_succeeds_and_saves_key(self):
        key = f"teachers/{self.teacher.id}/profile.jpg"
        self.s3.put(key)

        self.service.confirm_profile_picture_upload(self.teacher.id, key, self.s3)

        self.teacher.refresh_from_db()
        self.assertEqual(self.teacher.user.profile_picture_key, key)

    def test_confirm_rejects_a_key_belonging_to_another_teacher(self):
        foreign_key = f"teachers/{self.other_teacher.id}/profile.jpg"
        self.s3.put(foreign_key)

        with self.assertRaises(ValueError):
            self.service.confirm_profile_picture_upload(self.teacher.id, foreign_key, self.s3)

    def test_confirm_rejects_oversized_object_and_deletes_it(self):
        key = f"teachers/{self.teacher.id}/profile.jpg"
        self.s3.put(key, content_length = 10 * 1024 * 1024)

        with self.assertRaises(ValueError):
            self.service.confirm_profile_picture_upload(self.teacher.id, key, self.s3)

        self.assertIn(key, self.s3.deleted_keys)

    def test_replacing_picture_deletes_old_object_only_after_new_one_confirmed(self):
        old_key = f"teachers/{self.teacher.id}/profile.jpg"
        self.s3.put(old_key)
        self.service.confirm_profile_picture_upload(self.teacher.id, old_key, self.s3)

        new_key = f"teachers/{self.teacher.id}/profile.webp"
        self.s3.put(new_key)
        self.service.confirm_profile_picture_upload(self.teacher.id, new_key, self.s3)

        self.teacher.refresh_from_db()
        self.assertEqual(self.teacher.user.profile_picture_key, new_key)
        self.assertIn(old_key, self.s3.deleted_keys)

    def test_confirm_invalidates_detail_cache(self):
        cached_before = self.service.get(self.teacher.id)
        self.assertIsNone(cached_before.user.profile_picture_key)

        key = f"teachers/{self.teacher.id}/profile.jpg"
        self.s3.put(key)
        self.service.confirm_profile_picture_upload(self.teacher.id, key, self.s3)

        cached_after = self.service.get(self.teacher.id)
        self.assertEqual(cached_after.user.profile_picture_key, key)


class ViewUrlAndDeleteTests(ProfilePictureServiceTestBase):

    def test_view_url_is_none_when_no_picture_set(self):
        self.assertIsNone(self.service.get_profile_picture_view_url(self.teacher.id, self.s3))

    def test_view_url_generated_fresh(self):
        key = f"teachers/{self.teacher.id}/profile.jpg"
        self.s3.put(key)
        self.service.confirm_profile_picture_upload(self.teacher.id, key, self.s3)

        url = self.service.get_profile_picture_view_url(self.teacher.id, self.s3)
        self.assertIn(key, url)

    def test_delete_removes_s3_object_and_clears_db_key(self):
        key = f"teachers/{self.teacher.id}/profile.jpg"
        self.s3.put(key)
        self.service.confirm_profile_picture_upload(self.teacher.id, key, self.s3)

        self.service.delete_profile_picture(self.teacher.id, self.s3)

        self.teacher.refresh_from_db()
        self.assertIsNone(self.teacher.user.profile_picture_key)
        self.assertIn(key, self.s3.deleted_keys)

    def test_delete_is_a_no_op_when_no_picture_set(self):
        self.service.delete_profile_picture(self.teacher.id, self.s3)
        self.assertEqual(self.s3.deleted_keys, [])


class ListPayloadTests(ProfilePictureServiceTestBase):

    def test_list_dto_carries_key_not_url(self):
        key = f"teachers/{self.teacher.id}/profile.jpg"
        self.s3.put(key)
        self.service.confirm_profile_picture_upload(self.teacher.id, key, self.s3)

        from teachers.mappers.teacher_mapper import TeacherMapper
        teacher = self.repository.get(self.teacher.id)
        dto = TeacherMapper.to_list_dto(teacher)

        self.assertEqual(dto["profile_picture_key"], key)
        self.assertNotIn("profile_picture_url", dto)

    def test_null_when_no_picture(self):
        from teachers.mappers.teacher_mapper import TeacherMapper
        dto = TeacherMapper.to_list_dto(self.repository.get(self.other_teacher.id))
        self.assertIsNone(dto["profile_picture_key"])


#Mimics a Django user: a missing reverse one-to-one raises ObjectDoesNotExist
#rather than AttributeError, which is what common.permissions._get_profile()
#catches. Matches teachers/tests' existing StubUser convention.
class ScopeStubUser:

    def __init__(self, is_authenticated = True, is_superuser = False, teacher = None, student = None):
        self.is_authenticated = is_authenticated
        self.is_superuser = is_superuser
        self._teacher = teacher
        self._student = student

    @property
    def teacher_profile(self):
        if self._teacher is None:
            raise ObjectDoesNotExist()
        return self._teacher

    @property
    def student_profile(self):
        if self._student is None:
            raise ObjectDoesNotExist()
        return self._student


#Permission matrix, mirrored from the student side: a teacher must not reach
#an arbitrary teacher's picture, and a student only reaches teachers of their
#own enrolled courses. These exercise the exact apply_data_scope() call the
#teacher profile-picture by-ID endpoint uses to authorize.
class ProfilePictureScopeTests(ProfilePictureServiceTestBase):

    def setUp(self):
        super().setUp()
        self.section = Section.objects.create(
            name = "A", department = self.department, semester_number = 1, academic_year = 2026,
        )
        self.course = Course.objects.create(name = "Intro", code = "CS101", credits = 3, department = self.department)
        self.offering = CourseOffering.objects.create(
            course = self.course, teacher = self.teacher, semester = "FALL",
            academic_year = 2026, section = self.section,
        )

        student_user = User.objects.create_user(
            email = "student@example.com", name = "Student One", password = "x", role = "student",
        )
        self.student = Student.objects.create(
            user = student_user, parents_phone_number = "1234567",
            department = self.department, section = self.section,
        )
        Enrollment.objects.create(student = self.student, course_offering = self.offering)

    def test_teacher_cannot_reach_another_teachers_scope(self):
        viewer = ScopeStubUser(teacher = self.teacher)

        queryset = apply_data_scope(viewer, Teacher.objects.all(), 'teacher')
        self.assertTrue(queryset.filter(id = self.teacher.id).exists())
        self.assertFalse(queryset.filter(id = self.other_teacher.id).exists())

    def test_student_reaches_only_their_enrolled_teachers(self):
        viewer = ScopeStubUser(student = self.student)

        queryset = apply_data_scope(viewer, Teacher.objects.all(), 'teacher')
        self.assertTrue(queryset.filter(id = self.teacher.id).exists())
        self.assertFalse(queryset.filter(id = self.other_teacher.id).exists())

    def test_admin_reaches_every_teacher(self):
        viewer = ScopeStubUser(is_superuser = True)

        queryset = apply_data_scope(viewer, Teacher.objects.all(), 'teacher')
        self.assertTrue(queryset.filter(id = self.teacher.id).exists())
        self.assertTrue(queryset.filter(id = self.other_teacher.id).exists())

    def test_teacher_reaches_their_own_enrolled_student(self):
        viewer = ScopeStubUser(teacher = self.teacher)

        queryset = apply_data_scope(viewer, Student.objects.all(), 'student')
        self.assertTrue(queryset.filter(id = self.student.id).exists())
