import fnmatch
from django.test import TestCase
from common.cache.cache_service import CacheService
from common.tests.test_base_entity_cache import FakeCacheClient
from departments.cache.department_cache import DepartmentCache
from departments.models import Department
from departments.repositories.department_repository import DepartmentRepository


class AnyUser:
    is_authenticated = True
    is_superuser = False


class DepartmentCacheConfigurationTests(TestCase):

    def setUp(self):
        self.department_cache = DepartmentCache(CacheService())

    def test_ttl_is_long_because_departments_embed_no_foreign_data(self):
        self.assertEqual(self.department_cache.list_timeout, 600)

    def test_scope_is_shared_across_every_viewer(self):
        #Departments are never passed through apply_data_scope, so keying per
        #user would fragment the cache into identical copies.
        admin = AnyUser()
        admin.is_superuser = True

        self.assertEqual(self.department_cache.scope_token_for(admin), "shared")
        self.assertEqual(self.department_cache.scope_token_for(AnyUser()), "shared")

    def test_list_and_reference_do_not_share_a_cache_entry(self):
        list_key = self.department_cache.list_key("shared", None, 1, 10)
        reference_key = self.department_cache.list_key(
            "shared", None, 1, 10, DepartmentCache.REFERENCE_FILTERS,
        )

        #Same rows, different projection - they must not collide.
        self.assertNotEqual(list_key, reference_key)

    def test_one_wildcard_invalidates_both_projections(self):
        pattern = self.department_cache.list_pattern()

        list_key = self.department_cache.list_key("shared", None, 1, 10)
        reference_key = self.department_cache.list_key(
            "shared", None, 1, 10, DepartmentCache.REFERENCE_FILTERS,
        )

        self.assertTrue(fnmatch.fnmatchcase(list_key, pattern))
        self.assertTrue(fnmatch.fnmatchcase(reference_key, pattern))


#Exercises the real invalidation path with an in-memory client: a single
#invalidate_on_write() must clear the admin list AND every dropdown page.
class DepartmentInvalidationTests(TestCase):

    def setUp(self):
        self.client = FakeCacheClient()
        self.department_cache = DepartmentCache(CacheService(client = self.client))

    def _populate(self):
        self.department_cache.get_or_load_list("shared", None, 1, 10, lambda: "list-p1")
        self.department_cache.get_or_load_list("shared", None, 2, 10, lambda: "list-p2")
        self.department_cache.get_or_load_list("shared", "eng", 1, 10, lambda: "list-search")
        self.department_cache.get_or_load_list(
            "shared", None, 1, 10, lambda: "ref-p1", filters = DepartmentCache.REFERENCE_FILTERS,
        )
        self.department_cache.get_or_load_list(
            "shared", None, 2, 10, lambda: "ref-p2", filters = DepartmentCache.REFERENCE_FILTERS,
        )

    def test_write_clears_list_and_reference_caches_together(self):
        self._populate()
        self.assertEqual(len(self.client.store), 5)

        self.department_cache.invalidate_on_write()

        self.assertEqual(self.client.store, {})

    def test_reference_pages_are_cached_independently(self):
        calls = []

        def loader(tag):
            def _loader():
                calls.append(tag)
                return tag

            return _loader

        args = ("shared", None)
        first = self.department_cache.get_or_load_list(
            *args, 1, 10, loader("p1"), filters = DepartmentCache.REFERENCE_FILTERS,
        )
        second = self.department_cache.get_or_load_list(
            *args, 1, 10, loader("ignored"), filters = DepartmentCache.REFERENCE_FILTERS,
        )

        self.assertEqual((first, second), ("p1", "p1"))
        self.assertEqual(calls, ["p1"])

    def test_reference_entries_carry_the_long_ttl(self):
        self.department_cache.get_or_load_list(
            "shared", None, 1, 10, lambda: "ref", filters = DepartmentCache.REFERENCE_FILTERS,
        )

        self.assertEqual(set(self.client.timeouts.values()), {600})


#Guards the soft-delete fix: the admin list and the dropdown must agree about
#which departments exist.
class SoftDeleteVisibilityTests(TestCase):

    def setUp(self):
        self.repository = DepartmentRepository()
        self.live = Department.objects.create(name = "Physics", code = "PHY")
        self.removed = Department.objects.create(name = "Alchemy", code = "ALC", is_deleted = True)

    def test_list_queryset_excludes_soft_deleted_rows(self):
        ids = set(self.repository.get_queryset_for_list().values_list("id", flat = True))

        self.assertIn(self.live.id, ids)
        self.assertNotIn(self.removed.id, ids)

    def test_list_and_reference_agree(self):
        list_ids = set(self.repository.get_queryset_for_list().values_list("id", flat = True))
        reference_ids = set(self.repository.get_queryset_for_reference().values_list("id", flat = True))

        self.assertEqual(list_ids, reference_ids)

    def test_search_also_excludes_soft_deleted_rows(self):
        ids = set(self.repository.get_queryset_for_list(search = "Alchemy").values_list("id", flat = True))

        self.assertEqual(ids, set())
