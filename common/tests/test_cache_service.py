from django.core.cache import cache
from django.test import TestCase
from common.cache.cache_service import CacheService


class CacheServiceTests(TestCase):

    def setUp(self):
        self.cache_service = CacheService()
        cache.clear()

    def test_build_key(self):
        self.assertEqual(self.cache_service.build_key("student", 5), "student:5")

    def test_set_and_get(self):
        key = self.cache_service.build_key("student", 5)
        self.cache_service.set(key, {"id": 5})

        self.assertEqual(self.cache_service.get(key), {"id": 5})

    def test_get_missing_returns_default(self):
        self.assertIsNone(self.cache_service.get("missing:key"))
        self.assertEqual(self.cache_service.get("missing:key", default = "fallback"), "fallback")

    def test_delete(self):
        key = self.cache_service.build_key("student", 5)
        self.cache_service.set(key, {"id": 5})
        self.cache_service.delete(key)

        self.assertIsNone(self.cache_service.get(key))

    def test_get_or_set_on_miss_calls_loader(self):
        calls = []

        def loader():
            calls.append(1)
            return "value"

        result = self.cache_service.get_or_set("miss:key", loader)

        self.assertEqual(result, "value")
        self.assertEqual(len(calls), 1)

    def test_get_or_set_on_hit_does_not_call_loader_again(self):
        calls = []

        def loader():
            calls.append(1)
            return "value"

        self.cache_service.get_or_set("hit:key", loader)
        result = self.cache_service.get_or_set("hit:key", loader)

        self.assertEqual(result, "value")
        self.assertEqual(len(calls), 1)

    def test_get_or_set_caches_none_without_recalling_loader(self):
        calls = []

        def loader():
            calls.append(1)
            return None

        first = self.cache_service.get_or_set("none:key", loader)
        second = self.cache_service.get_or_set("none:key", loader)

        self.assertIsNone(first)
        self.assertIsNone(second)
        self.assertEqual(len(calls), 1)
