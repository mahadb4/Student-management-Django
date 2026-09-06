from typing import Any, Callable, Optional
from django.core.cache import cache


_MISSING = object()

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

    #Deletes every key matching a glob pattern, e.g. "student:list:*".
    #Raises instead of no-opping: a silent failure here means list invalidation
    #stops working and stale pages are served with no visible symptom.
    def delete_pattern(self, pattern: str) -> int:
        if not hasattr(self.client, "delete_pattern"):
            raise NotImplementedError(
                f"Cache backend {type(self.client).__name__} does not support "
                f"delete_pattern(); list cache invalidation cannot work. "
                f"Configure a django_redis backend for the 'default' cache alias."
            )

        return self.client.delete_pattern(pattern)

    def get_or_set(
        self,
        key: str,
        loader: Callable[[], Any],
        timeout: Optional[int] = None
    ) -> Any:
        value = self.client.get(key, _MISSING)

        if value is _MISSING:
            value = loader()
            self.client.set(key, value, timeout)

        return value