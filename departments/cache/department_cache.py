from common.cache.base_entity_cache import BaseEntityCache


#Department-specific cache policy. Deliberately simpler than StudentCache /
#TeacherCache, because the Departments app is genuinely different:
#
#  * No data scoping. department_api never calls apply_data_scope(), and
#    apply_data_scope() returns departments unfiltered anyway - every permitted
#    viewer sees identical rows. So the scope dimension is a constant.
#  * No detail caching. The React admin page opens its edit modal straight from
#    the list row and never calls GET /departments/<id>/, so a detail cache would
#    serve no real frontend flow.
#  * A long TTL. Department DTOs embed no foreign data, so nothing but a
#    department write can make them stale - and that is invalidated explicitly.
class DepartmentCache(BaseEntityCache):

    #10 minutes. Safe because staleness can only come from department writes,
    #which drop every department:list:* key immediately.
    LIST_TIMEOUT_SECONDS = 600

    #Every permitted viewer sees the same rows, so one shared entry serves all.
    #Keeping the dimension (rather than dropping it) means introducing real
    #scoping later is a one-line change here.
    SHARED_SCOPE_TOKEN = "shared"

    #The list and reference endpoints are two different projections of the same
    #rows (DepartmentListDTO vs DepartmentReferenceDTO), so they must not share a
    #cache entry. Encoding the projection as a filter keeps both under the
    #department:list:* prefix, so one wildcard delete still invalidates both.
    REFERENCE_FILTERS = {"variant": "reference"}

    def __init__(self, cache_service):
        super().__init__(
            cache_service,
            namespace = "department",
            detail_timeout = None,
            list_timeout = self.LIST_TIMEOUT_SECONDS,
        )

    def scope_token_for(self, user) -> str:
        return self.SHARED_SCOPE_TOKEN
