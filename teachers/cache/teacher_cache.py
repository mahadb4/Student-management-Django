from common.cache.base_entity_cache import BaseEntityCache
from common.permissions import get_scope_identity


#Teacher-specific cache policy. Everything generic lives in BaseEntityCache.
class TeacherCache(BaseEntityCache):

    #Detail entries live until an explicit write invalidates them.
    #List entries expire quickly because they depend on scope, search and paging.
    LIST_TIMEOUT_SECONDS = 60

    def __init__(self, cache_service):
        super().__init__(
            cache_service,
            namespace = "teacher",
            detail_timeout = None,
            list_timeout = self.LIST_TIMEOUT_SECONDS,
        )

    #Identifies the viewer's data scope for cache keying.
    #Delegates to get_scope_identity(), the same helper apply_data_scope() uses,
    #so cache keys and authorization rules can never drift apart.
    #For 'teacher' scope that means: an admin sees every teacher, a teacher sees
    #only their own record, and a student sees teachers of their enrolled courses.
    #Produces: "anon" | "all" | "teacher:<id>" | "student:<id>" | "none"
    def scope_token_for(self, user) -> str:
        kind, profile = get_scope_identity(user)

        if profile is None:
            return kind

        return f"{kind}:{profile.id}"
