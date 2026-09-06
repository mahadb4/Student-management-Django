from common.cache.base_entity_cache import BaseEntityCache
from common.permissions import get_scope_identity


#Course-offering cache policy.
#
#No detail caching: the React admin page edits straight from the list row and
#never calls GET /course_offerings/<id>/.
#
#This entity needs TWO scope tokens, because its two read endpoints answer two
#different questions:
#
#  * the LIST endpoint asks "which offerings is this user entitled to see?"
#    -> apply_data_scope's 'courseoffering' branch -> identity-based token.
#  * the REFERENCE endpoint serves admin/teacher lookups AND the student
#    "Available Offerings" browse tab, which is discovery, not own-data.
#    For students that is section-based, so every student in a section shares
#    one entry (see reference_scope_token_for).
class CourseOfferingCache(BaseEntityCache):

    #60s: the DTOs embed course_name/code, teacher_name and section_name (three
    #other entities), and the list scope itself shifts when enrolments change.
    LIST_TIMEOUT_SECONDS = 60

    REFERENCE_FILTERS = {"variant": "reference"}

    def __init__(self, cache_service):
        super().__init__(
            cache_service,
            namespace = "courseoffering",
            detail_timeout = None,
            list_timeout = self.LIST_TIMEOUT_SECONDS,
        )

    #For the LIST endpoint: mirrors apply_data_scope(..., 'courseoffering').
    #admin -> every offering; teacher -> their own; student -> those they are
    #enrolled in. Identity-based, so scopes can never bleed into each other.
    def scope_token_for(self, user) -> str:
        kind, profile = get_scope_identity(user)

        if profile is None:
            return kind

        return f"{kind}:{profile.id}"

    #For the REFERENCE endpoint.
    #Admins and teachers keep their identity-based token, because that endpoint
    #still applies their normal data scope - widening it would hand a teacher
    #every offering in the system in their class-filter dropdown.
    #Students switch to a SECTION-based token: discovery is an exact section
    #match, identical for every student in that section, so keying it per student
    #would just store N copies of one payload. The old per-student enrolment
    #token is deliberately NOT reused here.
    def reference_scope_token_for(self, user) -> str:
        kind, profile = get_scope_identity(user)

        if kind == "student":
            return f"section:{profile.section_id if profile.section_id is not None else 'none'}"

        if profile is None:
            return kind

        return f"{kind}:{profile.id}"
