from django.core.exceptions import ObjectDoesNotExist
from django.test import TestCase
from common.cache.cache_service import CacheService
from common.permissions import apply_data_scope, get_scope_identity
from students.cache.student_cache import StudentCache


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


#Stands in for a queryset so scope routing can be asserted without touching the DB.
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


class ScopeTokenTests(TestCase):

    def setUp(self):
        self.student_cache = StudentCache(CacheService())

    def test_tokens_for_each_identity(self):
        self.assertEqual(self.student_cache.scope_token_for(ANON), "anon")
        self.assertEqual(self.student_cache.scope_token_for(ADMIN), "all")
        self.assertEqual(self.student_cache.scope_token_for(TEACHER), "teacher:7")
        self.assertEqual(self.student_cache.scope_token_for(STUDENT), "student:3")
        self.assertEqual(self.student_cache.scope_token_for(PROFILELESS), "none")

    def test_teacher_profile_wins_when_a_user_has_both(self):
        #Matches apply_data_scope(), which checks the teacher profile first.
        both = StubUser(teacher = StubProfile(7), student = StubProfile(3))
        self.assertEqual(self.student_cache.scope_token_for(both), "teacher:7")


#These guard the invariant that makes the list cache safe: cache keys and the
#actual authorization filtering must be derived from the same identity. If
#apply_data_scope() ever stops using get_scope_identity(), these fail.
class ScopeAlignmentTests(TestCase):

    def setUp(self):
        self.student_cache = StudentCache(CacheService())

    def test_apply_data_scope_returns_nothing_for_identities_that_see_nothing(self):
        for user in (ANON, PROFILELESS):
            self.assertEqual(apply_data_scope(user, FakeQuerySet(), 'student'), "EMPTY")

    def test_admin_scope_is_unfiltered(self):
        queryset = FakeQuerySet()
        self.assertIs(apply_data_scope(ADMIN, queryset, 'student'), queryset)
        self.assertEqual(self.student_cache.scope_token_for(ADMIN), "all")

    def test_teacher_scope_filters_by_the_same_profile_the_token_names(self):
        result = apply_data_scope(TEACHER, FakeQuerySet(), 'student')

        self.assertEqual(
            result.kwargs, {"enrollments__course_offering__teacher": TEACHER.teacher_profile},
        )
        #The token must name the very profile used in the filter.
        self.assertEqual(
            self.student_cache.scope_token_for(TEACHER),
            f"teacher:{TEACHER.teacher_profile.id}",
        )

    def test_student_scope_filters_by_the_same_profile_the_token_names(self):
        result = apply_data_scope(STUDENT, FakeQuerySet(), 'student')

        self.assertEqual(result.kwargs, {"id": STUDENT.student_profile.id})
        self.assertEqual(
            self.student_cache.scope_token_for(STUDENT),
            f"student:{STUDENT.student_profile.id}",
        )

    def test_identity_helper_is_model_type_independent(self):
        #The same identity drives every model_type; only the filter differs.
        for user, expected_kind in (
            (ANON, "anon"), (ADMIN, "all"), (TEACHER, "teacher"),
            (STUDENT, "student"), (PROFILELESS, "none"),
        ):
            kind, _ = get_scope_identity(user)
            self.assertEqual(kind, expected_kind)


class StudentCacheConfigurationTests(TestCase):

    def setUp(self):
        self.student_cache = StudentCache(CacheService())

    def test_detail_never_expires_but_lists_do(self):
        self.assertIsNone(self.student_cache.detail_timeout)
        self.assertEqual(self.student_cache.list_timeout, 60)
