from common.cache.base_entity_cache import BaseEntityCache


#Course-specific cache policy.
#
#Shared scope: course_api never calls apply_data_scope, and apply_data_scope
#returns courses unfiltered anyway (model_type in ["course","department"]), so
#every permitted viewer sees identical rows.
#
#Detail IS cached here, unlike Departments/Sections: the React admin page calls
#courseService.getById() to populate its edit form (Courses.tsx:76).
class CourseCache(BaseEntityCache):

    #60s: CourseListDTO embeds department_name AND teacher_name, and
    #CourseReferenceDTO embeds department_name. Nothing invalidates those when
    #the department or teacher is renamed, so the TTL is the only bound.
    LIST_TIMEOUT_SECONDS = 60

    SHARED_SCOPE_TOKEN = "shared"

    def __init__(self, cache_service):
        super().__init__(
            cache_service,
            namespace = "course",
            detail_timeout = None,
            list_timeout = self.LIST_TIMEOUT_SECONDS,
        )

    def scope_token_for(self, user) -> str:
        return self.SHARED_SCOPE_TOKEN

    #The reference endpoint narrows by department_id and semester_number, both
    #optional and sent as a subset by different callers. Pass ALREADY-NORMALIZED
    #values ("" -> None); None entries are dropped from the key.
    def reference_filters(self, department_id = None, semester_number = None) -> dict:
        return {
            "variant": "reference",
            "department_id": department_id,
            "semester_number": semester_number,
        }
