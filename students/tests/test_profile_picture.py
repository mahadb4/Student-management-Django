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
from students.cache.student_cache import StudentCache
from students.models import Student
from students.repositories.student_repository import StudentRepository
from students.services.student_service import StudentService
from students.services.student_validator import StudentValidator
from teachers.models import Teacher
from users.models import User


#A tiny but real, valid JPEG - confirm_profile_picture_upload now runs
#every upload through generate_avatar_thumbnail(), which needs bytes Pillow
#can actually decode, not just a byte count.
def _fake_uploaded_image_bytes():
    from io import BytesIO
    from PIL import Image

    buffer = BytesIO()
    Image.new("RGB", (20, 20), color = (200, 50, 50)).save(buffer, format = "JPEG")
    return buffer.getvalue()


#Hand-written in-memory fake of S3Service's public surface - no real AWS calls,
#matching this repo's existing stub/fake test convention.
class FakeS3Service:

    def __init__(self):
        self.objects = {}  # key -> content_length
        self.data = {}  # key -> bytes (only what get_object_bytes/put_object_bytes need)
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
        self.data.pop(key, None)
        self.deleted_keys.append(key)

    def get_object_bytes(self, key):
        return self.data.get(key) or _fake_uploaded_image_bytes()

    def put_object_bytes(self, key, data, content_type):
        self.objects[key] = len(data)
        self.data[key] = data

    #Test helper - simulates the frontend having actually uploaded to S3.
    def put(self, key, content_length = 1024):
        self.objects[key] = content_length
        self.data[key] = _fake_uploaded_image_bytes()


class ProfilePictureServiceTestBase(TestCase):

    def setUp(self):
        self.department = Department.objects.create(name = "Computing", code = "CMP")
        self.section = Section.objects.create(
            name = "A", department = self.department, semester_number = 1, academic_year = 2026,
        )
        self.repository = StudentRepository()
        self.service = StudentService(StudentValidator(), self.repository, StudentCache(CacheService()))
        self.s3 = FakeS3Service()

        self.student = self._make_student("student1@example.com", "Student One")
        self.other_student = self._make_student("student2@example.com", "Student Two")

    def _make_student(self, email, name):
        user = User.objects.create_user(email = email, name = name, password = "x", role = "student")
        return Student.objects.create(
            user = user, parents_phone_number = "1234567",
            department = self.department, section = self.section,
        )


class GenerateUploadUrlTests(ProfilePictureServiceTestBase):

    def test_generates_backend_derived_key_and_url(self):
        result = self.service.generate_profile_picture_upload_url(self.student.id, "image/jpeg", self.s3)

        self.assertEqual(result["key"], f"students/{self.student.id}/profile.jpg")
        self.assertIn(result["key"], result["upload_url"])
        self.assertEqual(result["content_type"], "image/jpeg")

    def test_rejects_unsupported_content_type(self):
        with self.assertRaises(ValueError):
            self.service.generate_profile_picture_upload_url(self.student.id, "application/pdf", self.s3)

    def test_raises_for_unknown_student(self):
        with self.assertRaises(Student.DoesNotExist):
            self.service.generate_profile_picture_upload_url(999999, "image/jpeg", self.s3)


class ConfirmUploadTests(ProfilePictureServiceTestBase):

    def test_confirm_fails_when_object_does_not_exist_in_s3(self):
        key = f"students/{self.student.id}/profile.jpg"
        with self.assertRaises(ValueError):
            self.service.confirm_profile_picture_upload(self.student.id, key, self.s3)

        self.student.refresh_from_db()
        self.assertIsNone(self.student.user.profile_picture_key)

    def test_confirm_succeeds_and_saves_key(self):
        key = f"students/{self.student.id}/profile.jpg"
        self.s3.put(key)

        self.service.confirm_profile_picture_upload(self.student.id, key, self.s3)

        self.student.refresh_from_db()
        self.assertEqual(self.student.user.profile_picture_key, key)

    def test_confirm_rejects_a_key_belonging_to_another_student(self):
        foreign_key = f"students/{self.other_student.id}/profile.jpg"
        self.s3.put(foreign_key)

        with self.assertRaises(ValueError):
            self.service.confirm_profile_picture_upload(self.student.id, foreign_key, self.s3)

        self.student.refresh_from_db()
        self.assertIsNone(self.student.user.profile_picture_key)

    def test_confirm_rejects_oversized_object_and_deletes_it(self):
        key = f"students/{self.student.id}/profile.jpg"
        self.s3.put(key, content_length = 10 * 1024 * 1024)  # 10MB > 5MB limit

        with self.assertRaises(ValueError):
            self.service.confirm_profile_picture_upload(self.student.id, key, self.s3)

        self.assertIn(key, self.s3.deleted_keys)
        self.student.refresh_from_db()
        self.assertIsNone(self.student.user.profile_picture_key)

    def test_replacing_picture_deletes_old_object_only_after_new_one_confirmed(self):
        old_key = f"students/{self.student.id}/profile.jpg"
        self.s3.put(old_key)
        self.service.confirm_profile_picture_upload(self.student.id, old_key, self.s3)

        new_key = f"students/{self.student.id}/profile.png"
        self.s3.put(new_key)
        self.service.confirm_profile_picture_upload(self.student.id, new_key, self.s3)

        self.student.refresh_from_db()
        self.assertEqual(self.student.user.profile_picture_key, new_key)
        self.assertIn(old_key, self.s3.deleted_keys)

    def test_confirm_invalidates_detail_cache(self):
        #Warm the detail cache with the pre-upload state.
        cached_before = self.service.get(self.student.id)
        self.assertIsNone(cached_before.user.profile_picture_key)

        key = f"students/{self.student.id}/profile.jpg"
        self.s3.put(key)
        self.service.confirm_profile_picture_upload(self.student.id, key, self.s3)

        cached_after = self.service.get(self.student.id)
        self.assertEqual(cached_after.user.profile_picture_key, key)


class ViewUrlAndDeleteTests(ProfilePictureServiceTestBase):

    def test_view_url_is_none_when_no_picture_set(self):
        self.assertIsNone(self.service.get_profile_picture_view_url(self.student.id, self.s3))

    def test_view_url_generated_fresh_and_not_stored_anywhere(self):
        key = f"students/{self.student.id}/profile.jpg"
        self.s3.put(key)
        self.service.confirm_profile_picture_upload(self.student.id, key, self.s3)

        url = self.service.get_profile_picture_view_url(self.student.id, self.s3)
        self.assertIn(key, url)
        #The DB only ever holds the key, never the URL.
        self.student.refresh_from_db()
        self.assertEqual(self.student.user.profile_picture_key, key)
        self.assertNotIn("profile_picture_url", vars(self.student))

    def test_delete_removes_s3_object_and_clears_db_key(self):
        key = f"students/{self.student.id}/profile.jpg"
        self.s3.put(key)
        self.service.confirm_profile_picture_upload(self.student.id, key, self.s3)

        self.service.delete_profile_picture(self.student.id, self.s3)

        self.student.refresh_from_db()
        self.assertIsNone(self.student.user.profile_picture_key)
        self.assertIn(key, self.s3.deleted_keys)

    def test_delete_is_a_no_op_when_no_picture_set(self):
        self.service.delete_profile_picture(self.student.id, self.s3)  # must not raise
        self.assertEqual(self.s3.deleted_keys, [])


class ListPayloadTests(ProfilePictureServiceTestBase):

    def test_list_dto_carries_key_not_url(self):
        key = f"students/{self.student.id}/profile.jpg"
        self.s3.put(key)
        self.service.confirm_profile_picture_upload(self.student.id, key, self.s3)

        from students.mappers.student_mapper import StudentMapper
        student = self.repository.get(self.student.id)
        dto = StudentMapper.to_list_dto(student)

        self.assertEqual(dto["profile_picture_key"], key)
        self.assertNotIn("profile_picture_url", dto)

    def test_attach_profile_picture_urls_replaces_key_with_fresh_url(self):
        from common.utils import attach_profile_picture_urls

        results = [
            {"id": 1, "profile_picture_key": "students/1/profile.jpg"},
            {"id": 2, "profile_picture_key": None},
        ]
        attach_profile_picture_urls(results, self.s3)

        self.assertNotIn("profile_picture_key", results[0])
        self.assertIn("students/1/profile.jpg", results[0]["profile_picture_url"])
        self.assertIsNone(results[1]["profile_picture_url"])


#Mimics a Django user: a missing reverse one-to-one raises ObjectDoesNotExist
#rather than AttributeError, which is what common.permissions._get_profile()
#catches. Matches students/tests/test_student_cache.py's StubUser.
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


#Permission matrix: a student must not be able to reach another student's
#picture by changing an ID, a teacher only reaches students in their own
#course offerings, and admin (apply_data_scope kind "all") reaches everyone.
#These exercise the exact same apply_data_scope() call the profile-picture
#by-ID endpoint uses to authorize.
class ProfilePictureScopeTests(ProfilePictureServiceTestBase):

    def setUp(self):
        super().setUp()
        self.course = Course.objects.create(name = "Intro", code = "CS101", credits = 3, department = self.department)

        teacher_user = User.objects.create_user(
            email = "teacher@example.com", name = "Teacher One", password = "x", role = "teacher",
        )
        self.teacher = Teacher.objects.create(
            user = teacher_user, employee_id = "T1", phone_number = "123",
            department = self.department, designation = "Prof", qualification = "PhD",
            salary = 1000,
        )
        self.offering = CourseOffering.objects.create(
            course = self.course, teacher = self.teacher, semester = "FALL",
            academic_year = 2026, section = self.section,
        )
        Enrollment.objects.create(student = self.student, course_offering = self.offering)
        #other_student is deliberately NOT enrolled with this teacher.

    def test_student_cannot_reach_another_students_scope(self):
        viewer = ScopeStubUser(student = self.student)

        queryset = apply_data_scope(viewer, Student.objects.all(), 'student')
        self.assertTrue(queryset.filter(id = self.student.id).exists())
        self.assertFalse(queryset.filter(id = self.other_student.id).exists())

    def test_teacher_reaches_only_their_enrolled_students(self):
        viewer = ScopeStubUser(teacher = self.teacher)

        queryset = apply_data_scope(viewer, Student.objects.all(), 'student')
        self.assertTrue(queryset.filter(id = self.student.id).exists())
        self.assertFalse(queryset.filter(id = self.other_student.id).exists())

    def test_admin_reaches_every_student(self):
        viewer = ScopeStubUser(is_superuser = True)

        queryset = apply_data_scope(viewer, Student.objects.all(), 'student')
        self.assertTrue(queryset.filter(id = self.student.id).exists())
        self.assertTrue(queryset.filter(id = self.other_student.id).exists())

    def test_student_can_reach_their_enrolled_teacher(self):
        viewer = ScopeStubUser(student = self.student)

        queryset = apply_data_scope(viewer, Teacher.objects.all(), 'teacher')
        self.assertTrue(queryset.filter(id = self.teacher.id).exists())
