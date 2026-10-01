import fnmatch
from django.test import TestCase
from common.cache.cache_service import CacheService
from common.tests.test_base_entity_cache import FakeCacheClient
from departments.cache.department_cache import DepartmentCache
from sections.cache.section_cache import SectionCache


class AnyUser:
    is_authenticated = True
    is_superuser = False


class SectionCacheConfigurationTests(TestCase):

    def setUp(self):
        self.section_cache = SectionCache(CacheService())

    def test_ttl_is_short_because_sections_embed_department_name(self):
        #Both section projections carry department_name, which nothing invalidates
        #when a department is renamed - the TTL is what bounds that staleness.
        self.assertEqual(self.section_cache.list_timeout, 60)

    def test_scope_is_shared_across_every_viewer(self):
        admin = AnyUser()
        admin.is_superuser = True

        self.assertEqual(self.section_cache.scope_token_for(admin), "shared")
        self.assertEqual(self.section_cache.scope_token_for(AnyUser()), "shared")

    def test_list_and_reference_do_not_share_a_cache_entry(self):
        self.assertNotEqual(
            self.section_cache.list_key("shared", None, 1, 10),
            self.section_cache.list_key("shared", None, 1, 10, self.section_cache.reference_filters()),
        )


#The regression this whole filters dimension exists for.
#The Students form requests sections by department alone; the Course Offerings
#form requests them by department + semester + academic year. If those two shared
#a cache entry, one page would show sections from the wrong semester or year.
class ReferenceFilterIsolationTests(TestCase):

    def setUp(self):
        self.section_cache = SectionCache(CacheService())

    def key(self, **kwargs):
        return self.section_cache.list_key(
            "shared", None, 1, 10, self.section_cache.reference_filters(**kwargs),
        )

    def test_department_only_and_fully_qualified_requests_differ(self):
        students_page = self.key(department_id = 3)
        offerings_page = self.key(department_id = 3, semester_number = 2, academic_year = 2025)

        self.assertNotEqual(students_page, offerings_page)

    def test_each_parameter_independently_changes_the_key(self):
        base = self.key(department_id = 3, semester_number = 2, academic_year = 2025)

        self.assertNotEqual(base, self.key(department_id = 4, semester_number = 2, academic_year = 2025))
        self.assertNotEqual(base, self.key(department_id = 3, semester_number = 5, academic_year = 2025))
        self.assertNotEqual(base, self.key(department_id = 3, semester_number = 2, academic_year = 2026))

    def test_unfiltered_reference_differs_from_every_filtered_one(self):
        unfiltered = self.key()

        self.assertNotEqual(unfiltered, self.key(department_id = 3))
        self.assertNotEqual(unfiltered, self.key(semester_number = 2))
        self.assertNotEqual(unfiltered, self.key(academic_year = 2025))

    def test_filtered_reference_payloads_are_not_served_to_each_other(self):
        client = FakeCacheClient()
        section_cache = SectionCache(CacheService(client = client))
        calls = []

        def loader(tag):
            def _loader():
                calls.append(tag)
                return tag

            return _loader

        wide = section_cache.get_or_load_list(
            "shared", None, 1, 10, loader("dept-3-all"),
            filters = section_cache.reference_filters(department_id = 3),
        )
        narrow = section_cache.get_or_load_list(
            "shared", None, 1, 10, loader("dept-3-sem-2-2025"),
            filters = section_cache.reference_filters(
                department_id = 3, semester_number = 2, academic_year = 2025,
            ),
        )
        wide_again = section_cache.get_or_load_list(
            "shared", None, 1, 10, loader("SHOULD-NOT-RUN"),
            filters = section_cache.reference_filters(department_id = 3),
        )

        self.assertEqual((wide, narrow, wide_again), ("dept-3-all", "dept-3-sem-2-2025", "dept-3-all"))
        self.assertEqual(calls, ["dept-3-all", "dept-3-sem-2-2025"])


class SectionInvalidationTests(TestCase):

    def setUp(self):
        self.client = FakeCacheClient()
        self.section_cache = SectionCache(CacheService(client = self.client))

    def test_one_write_clears_list_and_every_filtered_dropdown(self):
        self.section_cache.get_or_load_list("shared", None, 1, 10, lambda: "list-p1")
        self.section_cache.get_or_load_list("shared", "cs", 1, 10, lambda: "list-search")
        self.section_cache.get_or_load_list(
            "shared", None, 1, 10, lambda: "ref-all",
            filters = self.section_cache.reference_filters(),
        )
        self.section_cache.get_or_load_list(
            "shared", None, 1, 10, lambda: "ref-dept3",
            filters = self.section_cache.reference_filters(department_id = 3),
        )
        self.section_cache.get_or_load_list(
            "shared", None, 1, 10, lambda: "ref-narrow",
            filters = self.section_cache.reference_filters(
                department_id = 3, semester_number = 2, academic_year = 2025,
            ),
        )

        self.assertEqual(len(self.client.store), 5)
        self.section_cache.invalidate_on_write()
        self.assertEqual(self.client.store, {})

    def test_every_reference_key_is_matched_by_the_list_pattern(self):
        pattern = self.section_cache.list_pattern()

        for filters in (
            None,
            self.section_cache.reference_filters(),
            self.section_cache.reference_filters(department_id = 3),
            self.section_cache.reference_filters(department_id = 3, semester_number = 2, academic_year = 2025),
        ):
            key = self.section_cache.list_key("shared", None, 1, 10, filters)
            self.assertTrue(fnmatch.fnmatchcase(key, pattern), key)

    def test_entries_carry_the_short_ttl(self):
        self.section_cache.get_or_load_list("shared", None, 1, 10, lambda: "x")
        self.assertEqual(set(self.client.timeouts.values()), {60})
