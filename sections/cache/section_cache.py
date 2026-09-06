from common.cache.base_entity_cache import BaseEntityCache


#Section-specific cache policy.
#
#Like DepartmentCache: no data scoping (section_api never calls apply_data_scope,
#and apply_data_scope has NO 'section' branch - passing a section queryset to it
#would fall through to queryset.none()), and no detail caching (the React admin
#page edits straight from the list row and never calls GET /sections/<id>/).
#
#UNLIKE DepartmentCache: a short TTL. Both section projections embed
#department_name, so renaming a department leaves section lists and dropdowns
#showing a stale label with nothing to invalidate them. The TTL is the only thing
#bounding that, so it tracks the dependency rather than the app's update rate.
class SectionCache(BaseEntityCache):

    #60s, matching Students/Teachers, which embed foreign names for the same reason.
    LIST_TIMEOUT_SECONDS = 60

    #Every permitted viewer sees the same rows.
    SHARED_SCOPE_TOKEN = "shared"

    def __init__(self, cache_service):
        super().__init__(
            cache_service,
            namespace = "section",
            detail_timeout = None,
            list_timeout = self.LIST_TIMEOUT_SECONDS,
        )

    def scope_token_for(self, user) -> str:
        return self.SHARED_SCOPE_TOKEN

    #The reference endpoint narrows by up to three optional parameters, and
    #different admin pages send different SUBSETS of them (the Students form sends
    #department_id alone; the Course Offerings form sends all three). Every one of
    #them must appear in the key, or one page's wider result would be served to
    #another page that asked for a narrower slice.
    #
    #Pass ALREADY-NORMALIZED values (the view turns "" into None), so that
    #"?department_id=3&academic_year=" and "?department_id=3" - which select the
    #same rows - share one entry. None values are dropped by the key builder.
    #
    #"variant" separates this projection from the list projection while keeping the
    #key under section:list:*, so one wildcard delete still invalidates both.
    def reference_filters(self, department_id = None, semester_number = None, academic_year = None) -> dict:
        return {
            "variant": "reference",
            "department_id": department_id,
            "semester_number": semester_number,
            "academic_year": academic_year,
        }
