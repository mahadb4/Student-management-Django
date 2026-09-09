from datetime import date
from django.test import TestCase
from common.cache.cache_service import CacheService
from common.messages import Messages
from course_offerings.cache.course_offering_cache import CourseOfferingCache
from course_offerings.models import CourseOffering
from course_offerings.repositories.course_offering_repository import CourseOfferingRepository
from course_offerings.services.course_offering_service import CourseOfferingService
from course_offerings.services.course_offering_validator import CourseOfferingValidator
from courses.models import Course
from departments.models import Department
from enrollments.cache.enrollment_cache import EnrollmentCache
from enrollments.models import Enrollment
from enrollments.repositories.enrollment_repository import EnrollmentRepository
from enrollments.services.enrollment_service import EnrollmentService
from enrollments.services.enrollment_validator import EnrollmentValidator
from sections.models import Section
from students.models import Student
from teachers.models import Teacher
from users.models import User


#End-to-end cover for the corrected "Available Offerings" flow.
#
#Before the fix, /course_offerings/reference/ applied apply_data_scope's student
#branch, returning ONLY offerings the student was already enrolled in. The React
#page then subtracted its enrolled offerings from that list (Courses.tsx:72),
#so "Available Offerings" was arithmetically always empty and self-enrollment
#was unreachable from the UI.
class StudentOfferingDiscoveryTests(TestCase):

    def setUp(self):
        self.department = Department.objects.create(name = "Computing", code = "CMP")
        self.section = Section.objects.create(
            name = "A", department = self.department, semester_number = 1, academic_year = 2026,
        )
        self.other_section = Section.objects.create(
            name = "B", department = self.department, semester_number = 1, academic_year = 2026,
        )

        self.user = User.objects.create_user(
            email = "s1@example.com", name = "S One", password = "x", role = "student",
        )
        self.student = Student.objects.create(
            user = self.user, parents_phone_number = "1234567",
            date_of_birth = date(2000, 1, 1), gender = "M",
            department = self.department, section = self.section,
        )

        self.teacher_user = User.objects.create_user(
            email = "t1@example.com", name = "T One", password = "x", role = "teacher",
        )
        self.teacher = Teacher.objects.create(
            user = self.teacher_user, employee_id = "E1",
            phone_number = "1234567", department = self.department,
            designation = "Lecturer", qualification = "MSc", gender = "M",
            date_of_birth = date(1980, 1, 1), date_of_joining = date(2020, 1, 1), salary = 1,
        )

        self.course_a = Course.objects.create(
            name = "Algorithms", code = "CS101", credits = 3, department = self.department,
        )
        self.course_b = Course.objects.create(
            name = "Databases", code = "CS102", credits = 3, department = self.department,
        )
        self.course_c = Course.objects.create(
            name = "Networks", code = "CS103", credits = 3, department = self.department,
        )

        #Two offerings in the student's own section, one in a different section.
        self.enrolled_offering = self._offering(self.course_a, self.section)
        self.available_offering = self._offering(self.course_b, self.section)
        self.other_section_offering = self._offering(self.course_c, self.other_section)

        Enrollment.objects.create(student = self.student, course_offering = self.enrolled_offering)

        self.service = CourseOfferingService(
            CourseOfferingValidator(),
            CourseOfferingRepository(),
            CourseOfferingCache(CacheService()),
        )
        self.enrollment_service = EnrollmentService(
            EnrollmentValidator(),
            EnrollmentRepository(),
            EnrollmentCache(CacheService()),
        )

    def _offering(self, course, section):
        return CourseOffering.objects.create(
            course = course, teacher = self.teacher, semester = CourseOffering.Semester.FALL,
            academic_year = 2026, section = section,
        )

    def _reference_ids(self):
        payload = self.service.get_reference_list(self.user, None, 1, 100)
        return {row["id"] for row in payload["results"]}

    def _available_ids(self):
        #Exactly what Courses.tsx computes: reference list minus already enrolled.
        enrolled = set(
            Enrollment.objects.filter(student = self.student, is_deleted = False)
            .values_list("course_offering_id", flat = True)
        )
        return self._reference_ids() - enrolled

    def test_discovery_is_not_limited_to_already_enrolled_offerings(self):
        #The regression: this used to equal exactly the enrolled set.
        self.assertIn(self.available_offering.id, self._reference_ids())

    def test_available_offerings_is_not_empty(self):
        self.assertEqual(self._available_ids(), {self.available_offering.id})

    def test_already_enrolled_offerings_are_excluded_from_available(self):
        self.assertNotIn(self.enrolled_offering.id, self._available_ids())

    def test_offerings_from_another_section_are_not_discoverable(self):
        #Mirrors _validate_student_section - the student could not enrol in these.
        self.assertNotIn(self.other_section_offering.id, self._reference_ids())

    def test_soft_deleted_offerings_are_excluded(self):
        #This path bypasses apply_data_scope, so the repository filters is_deleted itself.
        self.available_offering.is_deleted = True
        self.available_offering.save(update_fields = ["is_deleted"])

        self.assertNotIn(self.available_offering.id, self._reference_ids())

    def test_a_section_less_student_sees_only_section_less_offerings(self):
        section_less_offering = self._offering(self.course_c, None)
        self.student.section = None
        self.student.save(update_fields = ["section"])

        ids = self._reference_ids()

        self.assertIn(section_less_offering.id, ids)
        self.assertNotIn(self.available_offering.id, ids)

    def test_a_discoverable_offering_can_actually_be_enrolled_in(self):
        enrollment = self.enrollment_service.create({
            "student": self.student.id,
            "course_offering": self.available_offering.id,
        })

        self.assertEqual(enrollment.course_offering_id, self.available_offering.id)
        #And it then leaves the available list.
        self.assertNotIn(self.available_offering.id, self._available_ids())

    def test_enrollment_authorisation_is_unchanged_for_a_section_mismatch(self):
        #Discovery widened what is VISIBLE, never what may be enrolled in.
        with self.assertRaises(ValueError) as raised:
            self.enrollment_service.create({
                "student": self.student.id,
                "course_offering": self.other_section_offering.id,
            })

        self.assertEqual(str(raised.exception), Messages.ENROLLMENT_SECTION_MISMATCH)

    def test_duplicate_enrollment_is_still_rejected(self):
        with self.assertRaises(ValueError):
            self.enrollment_service.create({
                "student": self.student.id,
                "course_offering": self.enrolled_offering.id,
            })

    def test_inactive_offering_is_still_rejected_at_enrollment(self):
        #Rejected by EnrollmentValidator.validate(), which runs before
        #_validate_student_section and so reports INVALID_COURSE_OFFERING rather
        #than that method's own COURSE_OFFERING_INACTIVE. Either way the
        #enrollment is refused - discovery widened visibility, not authorisation.
        self.available_offering.is_active = False
        self.available_offering.save(update_fields = ["is_active"])

        with self.assertRaises(ValueError) as raised:
            self.enrollment_service.create({
                "student": self.student.id,
                "course_offering": self.available_offering.id,
            })

        self.assertEqual(
            str(raised.exception),
            Messages.INVALID_COURSE_OFFERING.format(self.available_offering.id),
        )

    def test_soft_deleted_student_is_rejected_with_a_validation_error(self):
        #Regression: the validator checked is_active but not is_deleted, so a
        #soft-deleted but still-active student passed it and then hit
        #_validate_student_section's Student.objects.get(..., is_deleted = False),
        #raising an uncaught Student.DoesNotExist - which enrollment_api does not
        #handle, so the request returned HTTP 500 instead of a 400.
        self.student.is_deleted = True
        self.student.save(update_fields = ["is_deleted"])

        with self.assertRaises(ValueError) as raised:
            self.enrollment_service.create({
                "student": self.student.id,
                "course_offering": self.available_offering.id,
            })

        self.assertEqual(
            str(raised.exception), Messages.INVALID_STUDENT.format(self.student.id),
        )

    def test_soft_deleted_student_does_not_raise_does_not_exist(self):
        #The specific failure mode: anything other than ValueError escapes
        #enrollment_api's except clauses and becomes a 500.
        self.student.is_deleted = True
        self.student.save(update_fields = ["is_deleted"])

        try:
            self.enrollment_service.create({
                "student": self.student.id,
                "course_offering": self.available_offering.id,
            })
        except ValueError:
            pass
        except Student.DoesNotExist:
            self.fail("soft-deleted student raised Student.DoesNotExist (HTTP 500) instead of ValueError")

    def test_soft_deleted_student_is_rejected_on_update_too(self):
        #update() runs the same validator, so it must reject identically.
        enrollment = Enrollment.objects.get(
            student = self.student, course_offering = self.enrolled_offering,
        )
        self.student.is_deleted = True
        self.student.save(update_fields = ["is_deleted"])

        with self.assertRaises(ValueError) as raised:
            self.enrollment_service.update(
                enrollment.id,
                {"student": self.student.id, "course_offering": self.enrolled_offering.id},
            )

        self.assertEqual(
            str(raised.exception), Messages.INVALID_STUDENT.format(self.student.id),
        )

    def test_a_live_active_student_is_still_accepted(self):
        #The fix must not reject ordinary students.
        enrollment = self.enrollment_service.create({
            "student": self.student.id,
            "course_offering": self.available_offering.id,
        })

        self.assertEqual(enrollment.student_id, self.student.id)

    def test_inactive_student_is_still_rejected_at_enrollment(self):
        self.student.is_active = False
        self.student.save(update_fields = ["is_active"])

        with self.assertRaises(ValueError) as raised:
            self.enrollment_service.create({
                "student": self.student.id,
                "course_offering": self.available_offering.id,
            })

        self.assertEqual(
            str(raised.exception), Messages.INVALID_STUDENT.format(self.student.id),
        )

    def test_teacher_reference_scope_is_not_widened_by_the_fix(self):
        teacher_user = User.objects.create_user(
            email = "t1u@example.com", name = "T One", password = "x", role = "teacher",
        )
        self.teacher.user = teacher_user
        self.teacher.save(update_fields = ["user"])

        payload = self.service.get_reference_list(teacher_user, None, 1, 100)
        ids = {row["id"] for row in payload["results"]}

        #The teacher owns all three offerings here, and still sees only their own -
        #the student fix must not have turned this into a system-wide list.
        self.assertEqual(
            ids,
            {self.enrolled_offering.id, self.available_offering.id, self.other_section_offering.id},
        )

        foreign_user = User.objects.create_user(
            email = "t2u@example.com", name = "T Two", password = "x", role = "teacher",
        )
        Teacher.objects.create(
            user = foreign_user, employee_id = "E2",
            phone_number = "1234567", department = self.department,
            designation = "Lecturer", qualification = "MSc", gender = "M",
            date_of_birth = date(1980, 1, 1), date_of_joining = date(2020, 1, 1), salary = 1,
        )

        foreign_payload = self.service.get_reference_list(foreign_user, None, 1, 100)

        self.assertEqual(foreign_payload["results"], [])
