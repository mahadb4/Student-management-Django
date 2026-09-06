from django.core.exceptions import ObjectDoesNotExist
from django.test import TestCase
from common.cache.cache_service import CacheService
from common.permissions import apply_data_scope
from common.tests.test_base_entity_cache import FakeCacheClient
from course_offerings.cache.course_offering_cache import CourseOfferingCache
from enrollments.cache.enrollment_cache import EnrollmentCache
from students.cache.student_cache import StudentCache


class StubProfile:

    def __init__(self, profile_id):
        self.id = profile_id


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


class EnrollmentScopeTests(TestCase):

    def setUp(self):
        self.enrollment_cache = EnrollmentCache(CacheService())

    def test_teacher_scope_filters_through_their_own_offerings(self):
        result = apply_data_scope(TEACHER, FakeQuerySet(), 'enrollment')

        self.assertEqual(result.kwargs, {"course_offering__teacher": TEACHER.teacher_profile})

    def test_student_scope_filters_to_their_own_enrollments(self):
        result = apply_data_scope(STUDENT, FakeQuerySet(), 'enrollment')

        self.assertEqual(result.kwargs, {"student": STUDENT.student_profile})

    def test_identities_that_see_nothing(self):
        for user in (ANON, PROFILELESS):
            self.assertEqual(apply_data_scope(user, FakeQuerySet(), 'enrollment'), "EMPTY")

    def test_cross_user_isolation(self):
        other_teacher = StubUser(teacher = StubProfile(9))
        other_student = StubUser(student = StubProfile(4))

        self.assertNotEqual(
            self.enrollment_cache.list_key(self.enrollment_cache.scope_token_for(TEACHER), None, 1, 10),
            self.enrollment_cache.list_key(self.enrollment_cache.scope_token_for(other_teacher), None, 1, 10),
        )
        self.assertNotEqual(
            self.enrollment_cache.list_key(self.enrollment_cache.scope_token_for(STUDENT), None, 1, 10),
            self.enrollment_cache.list_key(self.enrollment_cache.scope_token_for(other_student), None, 1, 10),
        )

    def test_a_teacher_and_a_student_with_the_same_profile_id_do_not_collide(self):
        same_id_student = StubUser(student = StubProfile(7))

        self.assertNotEqual(
            self.enrollment_cache.scope_token_for(TEACHER),
            self.enrollment_cache.scope_token_for(same_id_student),
        )


class EnrollmentSearchAndConfigTests(TestCase):

    def setUp(self):
        self.client = FakeCacheClient()
        self.enrollment_cache = EnrollmentCache(CacheService(client = self.client))

    def test_search_isolation(self):
        base = self.enrollment_cache.list_key("all", None, 1, 10)

        self.assertNotEqual(base, self.enrollment_cache.list_key("all", "ali", 1, 10))
        self.assertNotEqual(
            self.enrollment_cache.list_key("all", "ali", 1, 10),
            self.enrollment_cache.list_key("all", "usman", 1, 10),
        )

    def test_search_is_normalized(self):
        self.assertEqual(
            self.enrollment_cache.list_key("all", "ali", 1, 10),
            self.enrollment_cache.list_key("all", "  ALI ", 1, 10),
        )

    def test_no_detail_caching_configured_but_lists_expire(self):
        self.assertEqual(self.enrollment_cache.list_timeout, 60)

    def test_search_and_scope_combine_independently(self):
        self.assertNotEqual(
            self.enrollment_cache.list_key("teacher:7", "ali", 1, 10),
            self.enrollment_cache.list_key("student:3", "ali", 1, 10),
        )


class EnrollmentInvalidationTests(TestCase):

    def setUp(self):
        self.client = FakeCacheClient()
        self.enrollment_cache = EnrollmentCache(CacheService(client = self.client))

    def test_one_write_clears_every_scope_and_search(self):
        self.enrollment_cache.get_or_load_list("all", None, 1, 10, lambda: "a")
        self.enrollment_cache.get_or_load_list("teacher:7", None, 1, 10, lambda: "b")
        self.enrollment_cache.get_or_load_list("student:3", "ali", 1, 10, lambda: "c")

        self.assertEqual(len(self.client.store), 3)
        self.enrollment_cache.invalidate_on_write()
        self.assertEqual(self.client.store, {})

    def test_invalidation_is_namespace_local(self):
        #An enrollment write must not reach into other apps' namespaces. The
        #cross-app staleness that leaves behind is accepted and TTL-bounded.
        shared_client = FakeCacheClient()
        enrollment_cache = EnrollmentCache(CacheService(client = shared_client))
        student_cache = StudentCache(CacheService(client = shared_client))
        offering_cache = CourseOfferingCache(CacheService(client = shared_client))

        enrollment_cache.get_or_load_list("teacher:7", None, 1, 10, lambda: "enrollments")
        student_cache.get_or_load_list("teacher:7", None, 1, 10, lambda: "students")
        offering_cache.get_or_load_list("student:3", None, 1, 10, lambda: "offerings")

        enrollment_cache.invalidate_on_write()

        remaining = set(shared_client.store)
        self.assertEqual(len(remaining), 2)
        self.assertTrue(any(k.startswith("student:list:") for k in remaining))
        self.assertTrue(any(k.startswith("courseoffering:list:") for k in remaining))

