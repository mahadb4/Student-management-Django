from common.cache.base_entity_cache import BaseEntityCache
from common.permissions import get_scope_identity


#Enrollment cache policy.
#
#No detail caching: the React admin page edits from the list row and never calls
#GET /enrollments/<id>/.
#
#No reference caching here: /enrollments/ exposes only list and detail routes.
#The reference DTO is served from /students/me/courses/reference/, one of the
#/me/* endpoints left uncached.
class EnrollmentCache(BaseEntityCache):

    #60s. EnrollmentListDTO has the deepest dependency chain in the project -
    #student name/email, course name/code, section name (and teacher name in the
    #student variant) - none of which is invalidated by its owning app.
    #
    #Enrolment writes also shift OTHER apps' scopes (a teacher's student roster,
    #a student's visible offerings and teachers). That cross-app staleness is
    #accepted and TTL-bounded by deliberate decision; it is not a leak, because
    #every list key carries its own scope token and detail endpoints re-check
    #authorisation on every request without consulting any cache.
    LIST_TIMEOUT_SECONDS = 60

    def __init__(self, cache_service):
        super().__init__(
            cache_service,
            namespace = "enrollment",
            detail_timeout = None,
            list_timeout = self.LIST_TIMEOUT_SECONDS,
        )

    #Mirrors apply_data_scope(..., 'enrollment'): admin -> all; teacher -> those
    #in their own offerings; student -> their own.
    def scope_token_for(self, user) -> str:
        kind, profile = get_scope_identity(user)

        if profile is None:
            return kind

        return f"{kind}:{profile.id}"
