from django.core.exceptions import ObjectDoesNotExist
from django.test import TestCase
from common.cache.cache_service import CacheService
from common.permissions import apply_data_scope, get_scope_identity
from teachers.cache.teacher_cache import TeacherCache


class StubProfile:

    def __init__(self, profile_id):
        self.id = profile_id


#Mimics a Django user: a missing reverse one-to-one raises ObjectDoesNotExist
#rather than AttributeError, which is what _get_profile() catches.
class StubUser:

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


class FakeFilterResult:

    def __init__(self, kwargs):
        self.kwargs = kwargs

    def distinct(self):
        return self


class FakeQuerySet:

    def __init__(self):
        self.model = type("FakeModel", (), {})

    def filter(self, **kwargs):
        return FakeFilterResult(kwargs)

    def none(self):
        return "EMPTY"


ANON = StubUser(is_authenticated = False)
ADMIN = StubUser(is_superuser = True)
TEACHER = StubUser(teacher = StubProfile(7))
STUDENT = StubUser(student = StubProfile(3))
PROFILELESS = StubUser()


#The 'teacher' data scope differs from the 'student' one: a teacher sees only
#their OWN record, while a student sees teachers of their enrolled courses.
#These assert the cache token names the same identity the filter uses.
class TeacherScopeAlignmentTests(TestCase):

    def setUp(self):
        self.teacher_cache = TeacherCache(CacheService())

    def test_identities_that_see_nothing(self):
        for user in (ANON, PROFILELESS):
            self.assertEqual(apply_data_scope(user, FakeQuerySet(), 'teacher'), "EMPTY")

    def test_admin_scope_is_unfiltered(self):
        queryset = FakeQuerySet()
        self.assertIs(apply_data_scope(ADMIN, queryset, 'teacher'), queryset)
        self.assertEqual(self.teacher_cache.scope_token_for(ADMIN), "all")

    def test_teacher_sees_only_their_own_record(self):
        result = apply_data_scope(TEACHER, FakeQuerySet(), 'teacher')

        self.assertEqual(result.kwargs, {"id": TEACHER.teacher_profile.id})
        self.assertEqual(
            self.teacher_cache.scope_token_for(TEACHER),
            f"teacher:{TEACHER.teacher_profile.id}",
        )

    def test_student_sees_teachers_of_their_enrolled_courses(self):
        result = apply_data_scope(STUDENT, FakeQuerySet(), 'teacher')

        self.assertEqual(
            result.kwargs, {"course_offerings__enrollments__student": STUDENT.student_profile},
        )
        self.assertEqual(
            self.teacher_cache.scope_token_for(STUDENT),
            f"student:{STUDENT.student_profile.id}",
        )

    def test_scope_identity_is_shared_with_apply_data_scope(self):
        for user, expected_kind in (
            (ANON, "anon"), (ADMIN, "all"), (TEACHER, "teacher"),
            (STUDENT, "student"), (PROFILELESS, "none"),
        ):
            kind, _ = get_scope_identity(user)
            self.assertEqual(kind, expected_kind)


class TeacherCacheConfigurationTests(TestCase):

    def setUp(self):
        self.teacher_cache = TeacherCache(CacheService())

    def test_detail_key_namespace(self):
        self.assertEqual(self.teacher_cache.detail_key(12), "teacher:12")

    def test_detail_never_expires_but_lists_do(self):
        self.assertIsNone(self.teacher_cache.detail_timeout)
        self.assertEqual(self.teacher_cache.list_timeout, 60)
