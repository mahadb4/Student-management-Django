from typing import Any, Callable, Optional
from django.core.cache import cache

_MISSING = object()

# It actually communicates with Django's cache backend, which is Redis in our case
# Low-level cache operations
class CacheService:

    def __init__(self, client=cache):
        self.client = client

    def build_key(self, namespace: str, identifier: Any) -> str:
        return f"{namespace}:{identifier}"

    def get(self, key: str, default: Any = None) -> Any:
        return self.client.get(key, default)

    def set(self, key: str, value: Any, timeout: Optional[int] = None) -> None:
        self.client.set(key, value, timeout)

    def delete(self, key: str) -> None:
        self.client.delete(key)

    def delete_pattern(self, pattern: str) -> int:
        if not hasattr(self.client, "delete_pattern"):
            raise NotImplementedError(
                f"Cache backend {type(self.client).__name__} does not support "
                f"delete_pattern(); list cache invalidation cannot work. "
                f"Configure a django_redis backend for the 'default' cache alias."
            )

        return self.client.delete_pattern(pattern)

    # loader = a function that knows how to fetch the data when the cache doesn't have it.
    def get_or_set(
        self,
        key: str,
        # Callable basically means: "This thing can be called like a function
        # The loader is a callable function that retrieves the data from the source
        # usually the database, when the requested data is not found in the cache.
        loader: Callable[[], Any], 
        timeout: Optional[int] = None
    ) -> Any:
        value = self.client.get(key, _MISSING)

        if value is _MISSING:
            value = loader()
            self.client.set(key, value, timeout)

        return value