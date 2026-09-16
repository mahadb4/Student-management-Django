import hashlib
from typing import Any, Callable, Generic, Optional

# Generic entity caching (keys, TTL, invalidation) with no per-model knowledge.
class BaseEntityCache:

    def __init__(
        self,
        cache_service,
        namespace: str,
        detail_timeout: Optional[int] = None,
        list_timeout: Optional[int] = 60,
    ):
    
        self.cache = cache_service
        self.namespace = namespace
        self.detail_timeout = detail_timeout
        self.list_timeout = list_timeout

    def detail_key(self, object_id: Any) -> str:
        return self.cache.build_key(self.namespace, object_id)

    # page/page_size must already be normalized by the caller so equivalent
    # requests share one cache entry. filters must include anything that
    # changes which rows come back, or a filtered result could leak elsewhere.
    def list_key(
        self,
        scope_token: str,
        search: Optional[str],
        page: int,
        page_size: int,
        filters: Optional[dict] = None,
    ) -> str:
        return (
            f"{self.namespace}:list:{scope_token}:{self._search_token(search)}"
            f":{self._filters_token(filters)}:{page}:{page_size}"
        )

    def list_pattern(self) -> str:
        return f"{self.namespace}:list:*"

    # Search text is user input, so it's normalized and hashed rather than
    # embedded raw in a Redis key.
    @staticmethod
    def _search_token(search: Optional[str]) -> str:
        if search is None:
            return "none"

        normalized = search.strip().lower()

        if not normalized:
            return "none"

        return hashlib.md5(normalized.encode("utf-8")).hexdigest()[:10]


    @staticmethod
    def _filters_token(filters: Optional[dict]) -> str:
        if not filters:
            return "none"

        present = {key: value for key, value in filters.items() if value is not None}

        if not present:
            return "none"

        canonical = "&".join(f"{key}={present[key]}" for key in sorted(present))

        return hashlib.md5(canonical.encode("utf-8")).hexdigest()[:10]

    def get_or_load_detail(self, object_id: Any, loader: Callable[[], Any]) -> Any:
        return self.cache.get_or_set(self.detail_key(object_id), loader, self.detail_timeout)

    def get_or_load_list(
        self,
        scope_token: str,
        search: Optional[str],
        page: int,
        page_size: int,
        loader: Callable[[], Any],
        filters: Optional[dict] = None,
    ) -> Any:
        key = self.list_key(scope_token, search, page, page_size, filters)
        return self.cache.get_or_set(key, loader, self.list_timeout)

    def invalidate_detail(self, object_id: Any) -> None:
        self.cache.delete(self.detail_key(object_id))

    # Drops every cached list page across all scopes/searches/page sizes.
    # Blunt by design: computing exactly which pages a write affects is far
    # more expensive and error-prone than rebuilding them on next request.
    def invalidate_lists(self) -> int:
        return self.cache.delete_pattern(self.list_pattern())

    def invalidate_on_write(self, object_id: Any = None) -> None:
        if object_id is not None:
            self.invalidate_detail(object_id)

        self.invalidate_lists()
