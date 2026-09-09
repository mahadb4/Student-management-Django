from common.cache.base_entity_cache import BaseEntityCache
from common.permissions import get_scope_identity


#Student-specific cache policy. Everything generic lives in BaseEntityCache.
class StudentCache(BaseEntityCache):

# Use student as my namespace, detail cache doesn't expire automatically,
# list cache lasts 60 seconds, and student cache needs to know which user's scope we're dealing with.
    LIST_TIMEOUT_SECONDS = 60

    def __init__(self, cache_service):
        super().__init__(
            cache_service,
            namespace = "student",
            detail_timeout = None,
            list_timeout = self.LIST_TIMEOUT_SECONDS,
        )

    # What data is this user allowed to see?
    def scope_token_for(self, user) -> str:
        kind, profile = get_scope_identity(user)

        if profile is None:
            return kind

        return f"{kind}:{profile.id}"
