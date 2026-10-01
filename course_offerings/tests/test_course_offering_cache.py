import fnmatch
from django.core.exceptions import ObjectDoesNotExist
from django.test import TestCase
from common.cache.cache_service import CacheService
from common.permissions import apply_data_scope
from common.tests.test_base_entity_cache import FakeCacheClient
from course_offerings.cache.course_offering_cache import CourseOfferingCache


class StubProfile:

    def __init__(self, profile_id, section_id = None):
        self.id = profile_id
        self.section_id = section_id


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


ADMIN = StubUser(is_superuser = True)
TEACHER = StubUser(teacher = StubProfile(7))
STUDENT_A = StubUser(student = StubProfile(3, section_id = 11))
STUDENT_B = StubUser(student = StubProfile(4, section_id = 11))
STUDENT_C = StubUser(student = StubProfile(5, section_id = 22))
STUDENT_NO_SECTION = StubUser(student = StubProfile(6, section_id = None))


class ListScopeTests(TestCase):
    #The LIST endpoint keeps the identity-based scope, matching apply_data_scope.

    def setUp(self):
        self.offering_cache = CourseOfferingCache(CacheService())

    def test_tokens_match_apply_data_scope_identities(self):
        self.assertEqual(self.offering_cache.scope_token_for(ADMIN), "all")
        self.assertEqual(self.offering_cache.scope_token_for(TEACHER), "teacher:7")
        self.assertEqual(self.offering_cache.scope_token_for(STUDENT_A), "student:3")

    def test_teacher_scope_filters_by_the_profile_the_token_names(self):
        result = apply_data_scope(TEACHER, FakeQuerySet(), 'courseoffering')

        self.assertEqual(result.kwargs, {"teacher": TEACHER.teacher_profile})

    def test_student_list_scope_is_enrollment_based(self):
        result = apply_data_scope(STUDENT_A, FakeQuerySet(), 'courseoffering')

        self.assertEqual(result.kwargs, {"enrollments__student": STUDENT_A.student_profile})

    def test_cross_user_isolation(self):
        other_teacher = StubUser(teacher = StubProfile(9))

        self.assertNotEqual(
            self.offering_cache.list_key(self.offering_cache.scope_token_for(TEACHER), None, 1, 10),
            self.offering_cache.list_key(self.offering_cache.scope_token_for(other_teacher), None, 1, 10),
        )
        self.assertNotEqual(
            self.offering_cache.list_key(self.offering_cache.scope_token_for(STUDENT_A), None, 1, 10),
            self.offering_cache.list_key(self.offering_cache.scope_token_for(STUDENT_C), None, 1, 10),
        )


class ReferenceScopeTests(TestCase):
    #The REFERENCE endpoint answers a different question for students: discovery,
    #which is section-matched, NOT their enrollment-based own-data scope.

    def setUp(self):
        self.offering_cache = CourseOfferingCache(CacheService())

    def test_admin_and_teacher_keep_their_identity_token(self):
        #Widening these would put every offering in a teacher's class dropdown.
        self.assertEqual(self.offering_cache.reference_scope_token_for(ADMIN), "all")
        self.assertEqual(self.offering_cache.reference_scope_token_for(TEACHER), "teacher:7")

    def test_students_use_a_section_token_not_a_student_token(self):
        token = self.offering_cache.reference_scope_token_for(STUDENT_A)

        self.assertEqual(token, "section:11")
        #The old per-student enrollment token must NOT be reused here.
        self.assertNotEqual(token, self.offering_cache.scope_token_for(STUDENT_A))

    def test_students_in_the_same_section_share_one_cache_entry(self):
        #Discovery is identical for them, so keying per student would store copies.
        self.assertEqual(
            self.offering_cache.reference_scope_token_for(STUDENT_A),
            self.offering_cache.reference_scope_token_for(STUDENT_B),
        )

    def test_students_in_different_sections_do_not_share_an_entry(self):
        self.assertNotEqual(
            self.offering_cache.reference_scope_token_for(STUDENT_A),
            self.offering_cache.reference_scope_token_for(STUDENT_C),
        )

    def test_section_less_student_gets_its_own_token(self):
        token = self.offering_cache.reference_scope_token_for(STUDENT_NO_SECTION)

        self.assertEqual(token, "section:none")
        self.assertNotEqual(token, self.offering_cache.reference_scope_token_for(STUDENT_A))

    def test_reference_and_list_never_share_an_entry(self):
        for user in (ADMIN, TEACHER, STUDENT_A):
            list_key = self.offering_cache.list_key(
                self.offering_cache.scope_token_for(user), None, 1, 10, {"section_id": None},
            )
            reference_key = self.offering_cache.list_key(
                self.offering_cache.reference_scope_token_for(user), None, 1, 10,
                CourseOfferingCache.REFERENCE_FILTERS,
            )
            self.assertNotEqual(list_key, reference_key)


class SectionFilterTests(TestCase):
    #The Admin Enrollments form passes section_id to narrow the offering dropdown
    #to what the student could actually enrol in.

    def setUp(self):
        self.offering_cache = CourseOfferingCache(CacheService())

    def key(self, section_id):
        return self.offering_cache.list_key("all", None, 1, 10, {"section_id": section_id})

    def test_section_filter_changes_the_key(self):
        self.assertNotEqual(self.key(None), self.key(11))
        self.assertNotEqual(self.key(11), self.key(22))

    def test_unfiltered_matches_an_explicit_none(self):
        self.assertEqual(self.key(None), self.offering_cache.list_key("all", None, 1, 10, {}))


class InvalidationTests(TestCase):

    def setUp(self):
        self.client = FakeCacheClient()
        self.offering_cache = CourseOfferingCache(CacheService(client = self.client))

    def test_one_write_clears_every_scope_and_projection(self):
        self.offering_cache.get_or_load_list("all", None, 1, 10, lambda: "admin", filters = {"section_id": None})
        self.offering_cache.get_or_load_list("teacher:7", None, 1, 10, lambda: "teacher")
        self.offering_cache.get_or_load_list("student:3", None, 1, 10, lambda: "student")
        self.offering_cache.get_or_load_list(
            "section:11", None, 1, 10, lambda: "discovery",
            filters = CourseOfferingCache.REFERENCE_FILTERS,
        )

        self.assertEqual(len(self.client.store), 4)
        self.offering_cache.invalidate_on_write()
        self.assertEqual(self.client.store, {})

    def test_every_key_is_matched_by_the_list_pattern(self):
        pattern = self.offering_cache.list_pattern()

        for scope, filters in (
            ("all", {"section_id": None}),
            ("teacher:7", {"section_id": 11}),
            ("section:11", CourseOfferingCache.REFERENCE_FILTERS),
        ):
            key = self.offering_cache.list_key(scope, None, 1, 10, filters)
            self.assertTrue(fnmatch.fnmatchcase(key, pattern), key)

    def test_entries_carry_the_short_ttl(self):
        self.offering_cache.get_or_load_list("all", None, 1, 10, lambda: "x")
        self.assertEqual(set(self.client.timeouts.values()), {60})
