import fnmatch
from django.test import TestCase
from common.cache.cache_service import CacheService
from common.tests.test_base_entity_cache import FakeCacheClient
from courses.cache.course_cache import CourseCache


class AnyUser:
    is_authenticated = True
    is_superuser = False


class CourseCacheConfigurationTests(TestCase):

    def setUp(self):
        self.course_cache = CourseCache(CacheService())

    def test_detail_is_cached_forever_but_lists_expire(self):
        #Detail is cached because the admin page fetches the full record to edit.
        self.assertIsNone(self.course_cache.detail_timeout)
        self.assertEqual(self.course_cache.list_timeout, 60)

    def test_ttl_is_short_because_courses_embed_department_and_teacher_names(self):
        self.assertEqual(self.course_cache.list_timeout, 60)

    def test_scope_is_shared_across_every_viewer(self):
        admin = AnyUser()
        admin.is_superuser = True

        self.assertEqual(self.course_cache.scope_token_for(admin), "shared")
        self.assertEqual(self.course_cache.scope_token_for(AnyUser()), "shared")

    def test_detail_key_namespace(self):
        self.assertEqual(self.course_cache.detail_key(7), "course:7")


class CourseDetailListReferenceSeparationTests(TestCase):

    def setUp(self):
        self.client = FakeCacheClient()
        self.course_cache = CourseCache(CacheService(client = self.client))

    def test_list_and_reference_do_not_share_an_entry(self):
        self.assertNotEqual(
            self.course_cache.list_key("shared", None, 1, 10),
            self.course_cache.list_key("shared", None, 1, 10, self.course_cache.reference_filters()),
        )

    def test_list_pattern_does_not_match_the_detail_key(self):
        self.assertFalse(
            fnmatch.fnmatchcase("course:7", self.course_cache.list_pattern())
        )

    def test_detail_survives_list_only_invalidation(self):
        self.course_cache.get_or_load_detail(7, lambda: {"id": 7})
        self.course_cache.get_or_load_list("shared", None, 1, 10, lambda: "list")
        self.course_cache.get_or_load_list(
            "shared", None, 1, 10, lambda: "ref", filters = self.course_cache.reference_filters(),
        )

        self.course_cache.invalidate_lists()

        self.assertEqual(self.client.get("course:7"), {"id": 7})
        self.assertEqual([k for k in self.client.store if ":list:" in k], [])

    def test_write_with_id_clears_detail_list_and_reference(self):
        self.course_cache.get_or_load_detail(7, lambda: {"id": 7})
        self.course_cache.get_or_load_list("shared", None, 1, 10, lambda: "list")
        self.course_cache.get_or_load_list(
            "shared", None, 1, 10, lambda: "ref", filters = self.course_cache.reference_filters(),
        )

        self.course_cache.invalidate_on_write(7)

        self.assertEqual(self.client.store, {})

    def test_create_path_clears_lists_but_keeps_other_details(self):
        self.course_cache.get_or_load_detail(7, lambda: {"id": 7})
        self.course_cache.get_or_load_list("shared", None, 1, 10, lambda: "list")

        #create() has no id to drop.
        self.course_cache.invalidate_on_write()

        self.assertEqual(self.client.get("course:7"), {"id": 7})
        self.assertIsNone(self.client.get("course:list:shared:none:none:1:10"))


class CourseReferenceFilterIsolationTests(TestCase):

    def setUp(self):
        self.course_cache = CourseCache(CacheService())

    def key(self, **kwargs):
        return self.course_cache.list_key(
            "shared", None, 1, 10, self.course_cache.reference_filters(**kwargs),
        )

    def test_each_parameter_independently_changes_the_key(self):
        base = self.key(department_id = 3, semester_number = 2)

        self.assertNotEqual(base, self.key(department_id = 4, semester_number = 2))
        self.assertNotEqual(base, self.key(department_id = 3, semester_number = 5))

    def test_unfiltered_differs_from_partially_filtered(self):
        unfiltered = self.key()

        self.assertNotEqual(unfiltered, self.key(department_id = 3))
        self.assertNotEqual(unfiltered, self.key(semester_number = 2))
        self.assertNotEqual(self.key(department_id = 3), self.key(department_id = 3, semester_number = 2))

    def test_omitted_and_empty_parameters_share_one_entry(self):
        self.assertEqual(self.key(department_id = 3), self.key(department_id = 3, semester_number = None))

