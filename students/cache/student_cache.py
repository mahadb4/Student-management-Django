from common.cache.base_entity_cache import BaseEntityCache
from common.permissions import get_scope_identity


#Student-specific cache policy. Everything generic lives in BaseEntityCache.
class StudentCache(BaseEntityCache):

    #Detail entries live until an explicit write invalidates them.
    #List entries expire quickly because they depend on scope, search and paging.
    LIST_TIMEOUT_SECONDS = 60

    def __init__(self, cache_service):
        super().__init__(
            cache_service,
            namespace = "student",
            detail_timeout = None,
            list_timeout = self.LIST_TIMEOUT_SECONDS,
        )

    #Identifies the viewer's data scope for cache keying.
    #Delegates to get_scope_identity(), the same helper apply_data_scope() uses,
    #so cache keys and authorization rules can never drift apart.
    #Produces: "anon" | "all" | "teacher:<id>" | "student:<id>" | "none"
    def scope_token_for(self, user) -> str:
        kind, profile = get_scope_identity(user)

        if profile is None:
            return kind

        return f"{kind}:{profile.id}"
