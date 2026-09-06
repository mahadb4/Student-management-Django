import fnmatch
from django.test import TestCase
from common.cache.base_entity_cache import BaseEntityCache
from common.cache.cache_service import CacheService


#In-memory stand-in for django_redis so these tests do not need a running Redis.
class FakeCacheClient:

    def __init__(self):
        self.store = {}
        self.timeouts = {}

    def get(self, key, default = None):
        return self.store.get(key, default)

    def set(self, key, value, timeout = None):
        self.store[key] = value
        self.timeouts[key] = timeout

    def delete(self, key):
        self.store.pop(key, None)
        self.timeouts.pop(key, None)

    def delete_pattern(self, pattern):
        matched = [key for key in self.store if fnmatch.fnmatchcase(key, pattern)]

        for key in matched:
            self.delete(key)

        return len(matched)


#A backend that cannot do wildcard deletes, e.g. LocMemCache.
class NoPatternCacheClient:

    def __init__(self):
        self.store = {}

    def get(self, key, default = None):
        return self.store.get(key, default)

    def set(self, key, value, timeout = None):
        self.store[key] = value

    def delete(self, key):
        self.store.pop(key, None)


class DeletePatternTests(TestCase):

    def test_delete_pattern_removes_matching_keys(self):
        client = FakeCacheClient()
        service = CacheService(client = client)

        service.set("student:list:all:none:none:1:10", {"a": 1})
        service.set("student:list:teacher:7:abc:2:50", {"b": 2})
        service.set("student:44", {"id": 44})

        deleted = service.delete_pattern("student:list:*")

        self.assertEqual(deleted, 2)
        #Detail keys must survive list invalidation.
        self.assertEqual(service.get("student:44"), {"id": 44})

    def test_delete_pattern_raises_on_unsupported_backend(self):
        service = CacheService(client = NoPatternCacheClient())

        #Must fail loudly: a silent no-op would leave stale list pages served forever.
        with self.assertRaises(NotImplementedError):
            service.delete_pattern("student:list:*")


class BaseEntityCacheKeyTests(TestCase):

    def setUp(self):
        self.client = FakeCacheClient()
        self.entity_cache = BaseEntityCache(
            CacheService(client = self.client), namespace = "student", list_timeout = 60,
        )

    def test_detail_key(self):
        self.assertEqual(self.entity_cache.detail_key(44), "student:44")

    def test_list_pattern_does_not_match_detail_keys(self):
        self.assertEqual(self.entity_cache.list_pattern(), "student:list:*")
        self.assertFalse(fnmatch.fnmatchcase("student:44", self.entity_cache.list_pattern()))

    def test_list_key_shape(self):
        #ns : list : scope : search : filters : page : page_size
        key = self.entity_cache.list_key("teacher:7", None, 1, 100)
        self.assertEqual(key, "student:list:teacher:7:none:none:1:100")

    def test_empty_and_none_search_share_one_token(self):
        self.assertEqual(
            self.entity_cache.list_key("all", None, 1, 10),
            self.entity_cache.list_key("all", "   ", 1, 10),
        )

    def test_search_is_normalized_before_hashing(self):
        #Case and surrounding whitespace must not fragment the cache.
        self.assertEqual(
            self.entity_cache.list_key("all", "mah", 1, 10),
            self.entity_cache.list_key("all", "  MAH ", 1, 10),
        )

    def test_different_searches_produce_different_keys(self):
        self.assertNotEqual(
            self.entity_cache.list_key("all", "mah", 1, 10),
            self.entity_cache.list_key("all", "ali", 1, 10),
        )

    def test_scope_page_and_size_all_affect_the_key(self):
        base = self.entity_cache.list_key("all", "mah", 1, 10)

        self.assertNotEqual(base, self.entity_cache.list_key("teacher:7", "mah", 1, 10))
        self.assertNotEqual(base, self.entity_cache.list_key("all", "mah", 2, 10))
        self.assertNotEqual(base, self.entity_cache.list_key("all", "mah", 1, 25))


class ListKeyFilterTests(TestCase):

    def setUp(self):
        self.entity_cache = BaseEntityCache(
            CacheService(client = FakeCacheClient()), namespace = "teacher",
        )

    def key(self, filters):
        return self.entity_cache.list_key("all", None, 1, 10, filters)

    def test_no_filters_variants_agree(self):
        #None, {} and an all-None mapping select the same rows.
        self.assertEqual(self.key(None), self.key({}))
        self.assertEqual(self.key(None), self.key({"department_id": None}))

    def test_filters_change_the_key(self):
        self.assertNotEqual(self.key(None), self.key({"department_id": 3}))
        self.assertNotEqual(self.key({"department_id": 3}), self.key({"department_id": 4}))

    def test_filter_ordering_does_not_fragment_the_cache(self):
        self.assertEqual(
            self.key({"department_id": 3, "semester_number": 2}),
            self.key({"semester_number": 2, "department_id": 3}),
        )

    def test_int_and_string_values_agree(self):
        #Query-string params arrive as strings; service callers may pass ints.
        self.assertEqual(self.key({"department_id": 3}), self.key({"department_id": "3"}))

    def test_unset_filters_are_dropped_not_encoded(self):
        self.assertEqual(
            self.key({"department_id": 3}),
            self.key({"department_id": 3, "academic_year": None}),
        )

    def test_distinct_filter_names_do_not_collide(self):
        self.assertNotEqual(self.key({"department_id": 3}), self.key({"semester_number": 3}))

    def test_filters_are_honoured_by_get_or_load_list(self):
        calls = []

        def loader(tag):
            def _loader():
                calls.append(tag)
                return tag

            return _loader

        a = self.entity_cache.get_or_load_list("all", None, 1, 10, loader("A"), {"department_id": 3})
        b = self.entity_cache.get_or_load_list("all", None, 1, 10, loader("B"), {"department_id": 4})
        a_again = self.entity_cache.get_or_load_list("all", None, 1, 10, loader("X"), {"department_id": 3})

        #Different filters must not share a cached payload; the same filter must hit.
        self.assertEqual((a, b, a_again), ("A", "B", "A"))
        self.assertEqual(calls, ["A", "B"])

    def test_filtered_entries_are_still_dropped_by_list_invalidation(self):
        self.entity_cache.get_or_load_list("all", None, 1, 10, lambda: "x", {"department_id": 3})
        self.assertEqual(self.entity_cache.invalidate_lists(), 1)


class BaseEntityCacheBehaviourTests(TestCase):

    def setUp(self):
        self.client = FakeCacheClient()
        self.entity_cache = BaseEntityCache(
            CacheService(client = self.client),
            namespace = "student",
            detail_timeout = None,
            list_timeout = 60,
        )
        self.calls = []

    def loader(self, value):
        def _loader():
            self.calls.append(value)
            return value

        return _loader

    def test_detail_miss_then_hit(self):
        first = self.entity_cache.get_or_load_detail(44, self.loader({"id": 44}))
        second = self.entity_cache.get_or_load_detail(44, self.loader({"id": 44}))

        self.assertEqual(first, {"id": 44})
        self.assertEqual(second, {"id": 44})
        #Loader ran only on the miss.
        self.assertEqual(len(self.calls), 1)

    def test_detail_is_cached_without_expiry(self):
        self.entity_cache.get_or_load_detail(44, self.loader({"id": 44}))
        self.assertIsNone(self.client.timeouts["student:44"])

    def test_list_miss_then_hit(self):
        payload = {"total_count": 1, "results": [{"id": 44}]}

        first = self.entity_cache.get_or_load_list("all", "mah", 1, 10, self.loader(payload))
        second = self.entity_cache.get_or_load_list("all", "mah", 1, 10, self.loader(payload))

        self.assertEqual(first, payload)
        self.assertEqual(second, payload)
        self.assertEqual(len(self.calls), 1)

    def test_list_is_cached_with_short_ttl(self):
        self.entity_cache.get_or_load_list("all", None, 1, 10, self.loader({"results": []}))
        self.assertEqual(self.client.timeouts["student:list:all:none:none:1:10"], 60)

    def test_different_scopes_do_not_share_cached_pages(self):
        teacher_a = self.entity_cache.get_or_load_list("teacher:1", None, 1, 10, self.loader("A"))
        teacher_b = self.entity_cache.get_or_load_list("teacher:2", None, 1, 10, self.loader("B"))

        #One teacher must never be served another teacher's cached page.
        self.assertEqual(teacher_a, "A")
        self.assertEqual(teacher_b, "B")

    def test_invalidate_detail_only_drops_that_entry(self):
        self.entity_cache.get_or_load_detail(44, self.loader({"id": 44}))
        self.entity_cache.get_or_load_detail(45, self.loader({"id": 45}))

        self.entity_cache.invalidate_detail(44)

        self.assertIsNone(self.client.get("student:44"))
        self.assertEqual(self.client.get("student:45"), {"id": 45})

    def test_invalidate_lists_drops_every_scope_search_and_page(self):
        self.entity_cache.get_or_load_list("all", None, 1, 10, self.loader("p1"))
        self.entity_cache.get_or_load_list("all", None, 2, 10, self.loader("p2"))
        self.entity_cache.get_or_load_list("teacher:7", "mah", 1, 50, self.loader("p3"))
        self.entity_cache.get_or_load_detail(44, self.loader({"id": 44}))

        deleted = self.entity_cache.invalidate_lists()

        self.assertEqual(deleted, 3)
        #Detail cache is untouched by list invalidation.
        self.assertEqual(self.client.get("student:44"), {"id": 44})

    def test_invalidate_on_write_with_id_drops_detail_and_lists(self):
        self.entity_cache.get_or_load_detail(44, self.loader({"id": 44}))
        self.entity_cache.get_or_load_list("all", None, 1, 10, self.loader("p1"))

        self.entity_cache.invalidate_on_write(44)

        self.assertEqual(self.client.store, {})

    def test_invalidate_on_write_without_id_drops_lists_only(self):
        #This is the create() path: no id existed before the write.
        self.entity_cache.get_or_load_detail(44, self.loader({"id": 44}))
        self.entity_cache.get_or_load_list("all", None, 1, 10, self.loader("p1"))

        self.entity_cache.invalidate_on_write()

        self.assertEqual(self.client.get("student:44"), {"id": 44})
        self.assertIsNone(self.client.get("student:list:all:none:none:1:10"))
