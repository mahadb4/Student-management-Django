"""
Proves, with real ORM tests against the actual database, that the existing
authorization functions already provide a safe data-scoping boundary for the
data the AI assistant retrieves. Does not introduce any new authorization
logic - only calls apply_data_scope, get_scope_identity, and
get_remarks_queryset_for_user against real fixtures.
"""
from datetime import date

from django.contrib.auth.models import AnonymousUser
from django.test import TestCase

from attendance.models import Attendance
from common.permissions import apply_data_scope, get_scope_identity
from course_offerings.models import CourseOffering
from courses.models import Course
from departments.models import Department
from enrollments.models import Enrollment
from remarks.authorization import get_remarks_queryset_for_user
from remarks.models import Remark
from sections.models import Section
from students.models import Student
from teachers.models import Teacher
from users.models import User


class ScopeAuthorizationTests(TestCase):
    """
    Fixture uses two independent teacher/offering pairs, so cross-teacher
    and cross-student leakage is always checkable.
    """

    def setUp(self):
        self.department = Department.objects.create(name="Computing", code="CMP")
        self.section = Section.objects.create(
            name="A", department=self.department, semester_number=1, academic_year=2026,
        )

        def make_teacher(email, name, employee_id):
            user = User.objects.create_user(email=email, name=name, password="x", role="teacher")
            return Teacher.objects.create(
                user=user, employee_id=employee_id, phone_number="1234567",
                department=self.department, designation="Lecturer", qualification="MSc",
                date_of_joining=date(2020, 1, 1), salary=1,
            )

        def make_student(email, name):
            user = User.objects.create_user(email=email, name=name, password="x", role="student")
            return Student.objects.create(
                user=user, parents_phone_number="1234567",
                department=self.department, section=self.section,
            )

        self.teacher_a = make_teacher("teacher.a@example.com", "Teacher A", "EMP-A")
        self.teacher_b = make_teacher("teacher.b@example.com", "Teacher B", "EMP-B")

        self.course_a = Course.objects.create(
            name="Databases", code="CS101", credits=3, department=self.department, teacher=self.teacher_a,
        )
        self.course_b = Course.objects.create(
            name="Networks", code="CS102", credits=3, department=self.department, teacher=self.teacher_b,
        )

        self.offering_a = CourseOffering.objects.create(
            course=self.course_a, teacher=self.teacher_a, semester=CourseOffering.Semester.FALL,
            academic_year=2026, section=self.section,
        )
        self.offering_b = CourseOffering.objects.create(
            course=self.course_b, teacher=self.teacher_b, semester=CourseOffering.Semester.FALL,
            academic_year=2026, section=self.section,
        )

        self.student_57 = make_student("student57@example.com", "Student 57")
        self.enrollment_57 = Enrollment.objects.create(
            student=self.student_57, course_offering=self.offering_a, status=Enrollment.Status.ACTIVE,
        )

        self.student_80 = make_student("student80@example.com", "Student 80")
        self.enrollment_80 = Enrollment.objects.create(
            student=self.student_80, course_offering=self.offering_b, status=Enrollment.Status.ACTIVE,
        )

        self.student_dropped = make_student("dropped@example.com", "Dropped Student")
        self.enrollment_dropped = Enrollment.objects.create(
            student=self.student_dropped, course_offering=self.offering_a, status=Enrollment.Status.DROPPED,
        )

        self.private_remark = Remark.objects.create(
            student=self.student_57, teacher=self.teacher_a, course_offering=self.offering_a,
            remark_text="Struggling with joins.", visibility=Remark.Visibility.PRIVATE,
        )
        self.visible_remark = Remark.objects.create(
            student=self.student_57, teacher=self.teacher_a, course_offering=self.offering_a,
            remark_text="Improved significantly.", visibility=Remark.Visibility.STUDENT_VISIBLE,
        )

        self.attendance_57 = Attendance.objects.create(
            enrollment=self.enrollment_57, date=date(2026, 2, 1), status=Attendance.Status.PRESENT,
        )
        self.attendance_80 = Attendance.objects.create(
            enrollment=self.enrollment_80, date=date(2026, 2, 1), status=Attendance.Status.ABSENT,
        )
        self.attendance_dropped = Attendance.objects.create(
            enrollment=self.enrollment_dropped, date=date(2026, 2, 1), status=Attendance.Status.ABSENT,
        )

        self.superuser = User.objects.create_superuser(
            email="root@example.com", name="Root", password="x",
        )

        # role="admin" but not a Django superuser, with neither teacher_profile
        # nor student_profile - resolves to kind "none", an existing behavior
        # this test suite locks in rather than fixes.
        self.admin_non_superuser = User.objects.create_user(
            email="admin@example.com", name="Admin", password="x", role="admin",
        )

    def test_student_sees_only_their_own_student_visible_remark_ids(self):
        qs = get_remarks_queryset_for_user(self.student_57.user)
        ids = set(qs.values_list("id", flat=True))
        self.assertEqual(ids, {self.visible_remark.id})

    def test_student_cannot_see_own_private_remark(self):
        qs = get_remarks_queryset_for_user(self.student_57.user)
        ids = set(qs.values_list("id", flat=True))
        self.assertNotIn(self.private_remark.id, ids)

    def test_student_cannot_see_another_students_remarks(self):
        qs = get_remarks_queryset_for_user(self.student_80.user, student_id=self.student_57.id)
        self.assertEqual(qs.count(), 0)

    def test_teacher_sees_remarks_for_their_own_offering_including_private(self):
        qs = get_remarks_queryset_for_user(self.teacher_a.user)
        ids = set(qs.values_list("id", flat=True))
        self.assertEqual(ids, {self.private_remark.id, self.visible_remark.id})

    def test_teacher_b_does_not_see_teacher_a_remarks(self):
        qs = get_remarks_queryset_for_user(self.teacher_b.user)
        self.assertEqual(qs.count(), 0)

    def test_teacher_probing_unauthorized_student_id_returns_empty(self):
        # Anti-enumeration: teacher_a has no relationship to student_80 at all,
        # so this must return an empty queryset, not an error or unfiltered one.
        qs = get_remarks_queryset_for_user(self.teacher_a.user, student_id=self.student_80.id)
        self.assertEqual(qs.count(), 0)

    def test_student_attendance_scope_contains_only_own_attendance(self):
        qs = apply_data_scope(self.student_57.user, Attendance.objects.all(), "attendance")
        ids = set(qs.values_list("id", flat=True))
        self.assertEqual(ids, {self.attendance_57.id})
        self.assertNotIn(self.attendance_80.id, ids)

    def test_teacher_attendance_scope_contains_only_own_offering_attendance(self):
        qs = apply_data_scope(self.teacher_a.user, Attendance.objects.all(), "attendance")
        ids = set(qs.values_list("id", flat=True))
        self.assertNotIn(self.attendance_80.id, ids)
        self.assertIn(self.attendance_57.id, ids)

    def test_teacher_b_does_not_see_teacher_a_attendance(self):
        qs = apply_data_scope(self.teacher_b.user, Attendance.objects.all(), "attendance")
        ids = set(qs.values_list("id", flat=True))
        self.assertNotIn(self.attendance_57.id, ids)
        self.assertNotIn(self.attendance_dropped.id, ids)

    def test_attendance_scope_does_not_exclude_dropped_enrollments(self):
        # Documents actual current behavior: apply_data_scope's "attendance"
        # branch has no status__in=[ACTIVE, COMPLETED] check, so a DROPPED
        # enrollment's attendance history still appears.
        student_qs = apply_data_scope(self.student_dropped.user, Attendance.objects.all(), "attendance")
        self.assertIn(self.attendance_dropped.id, set(student_qs.values_list("id", flat=True)))

        teacher_qs = apply_data_scope(self.teacher_a.user, Attendance.objects.all(), "attendance")
        self.assertIn(self.attendance_dropped.id, set(teacher_qs.values_list("id", flat=True)))

    def test_student_course_offering_scope_contains_only_authorized_offerings(self):
        qs = apply_data_scope(self.student_57.user, CourseOffering.objects.all(), "course_offering")
        ids = set(qs.values_list("id", flat=True))
        self.assertEqual(ids, {self.offering_a.id})

    def test_teacher_course_offering_scope_contains_only_taught_offerings(self):
        qs = apply_data_scope(self.teacher_a.user, CourseOffering.objects.all(), "course_offering")
        ids = set(qs.values_list("id", flat=True))
        self.assertEqual(ids, {self.offering_a.id})

    def test_course_offering_scope_does_not_exclude_dropped_enrollments(self):
        # Documents actual current behavior: apply_data_scope's "course_offering"
        # branch filters only on enrollment existence, with no status__in check,
        # so a DROPPED-only enrollment still sees that offering.
        qs = apply_data_scope(self.student_dropped.user, CourseOffering.objects.all(), "course_offering")
        ids = set(qs.values_list("id", flat=True))
        self.assertEqual(ids, {self.offering_a.id})

    def test_superuser_sees_all_remarks(self):
        qs = get_remarks_queryset_for_user(self.superuser)
        ids = set(qs.values_list("id", flat=True))
        self.assertEqual(ids, {self.private_remark.id, self.visible_remark.id})

    def test_superuser_sees_all_attendance(self):
        qs = apply_data_scope(self.superuser, Attendance.objects.all(), "attendance")
        ids = set(qs.values_list("id", flat=True))
        self.assertEqual(ids, {self.attendance_57.id, self.attendance_80.id, self.attendance_dropped.id})

    def test_superuser_sees_all_course_offerings(self):
        qs = apply_data_scope(self.superuser, CourseOffering.objects.all(), "course_offering")
        ids = set(qs.values_list("id", flat=True))
        self.assertEqual(ids, {self.offering_a.id, self.offering_b.id})

    def test_superuser_scope_identity_is_all(self):
        kind, profile = get_scope_identity(self.superuser)
        self.assertEqual(kind, "all")
        self.assertIsNone(profile)

    def test_anonymous_user_scope_identity_is_anon(self):
        kind, profile = get_scope_identity(AnonymousUser())
        self.assertEqual(kind, "anon")
        self.assertIsNone(profile)

    def test_anonymous_user_gets_no_attendance(self):
        qs = apply_data_scope(AnonymousUser(), Attendance.objects.all(), "attendance")
        self.assertEqual(qs.count(), 0)

    def test_anonymous_user_gets_no_remarks(self):
        qs = get_remarks_queryset_for_user(AnonymousUser())
        self.assertEqual(qs.count(), 0)

    def test_role_admin_non_superuser_scope_identity_is_none(self):
        kind, profile = get_scope_identity(self.admin_non_superuser)
        self.assertEqual(kind, "none")
        self.assertIsNone(profile)

    def test_role_admin_non_superuser_gets_no_attendance(self):
        qs = apply_data_scope(self.admin_non_superuser, Attendance.objects.all(), "attendance")
        self.assertEqual(qs.count(), 0)

    def test_role_admin_non_superuser_gets_no_remarks(self):
        qs = get_remarks_queryset_for_user(self.admin_non_superuser)
        self.assertEqual(qs.count(), 0)

    def test_unsupported_model_type_returns_empty_queryset(self):
        qs = apply_data_scope(self.student_57.user, Attendance.objects.all(), "not_a_real_model_type")
        self.assertEqual(qs.count(), 0)

    def test_superuser_bypasses_model_type_dispatch_entirely(self):
        # Documents actual behavior: for a superuser, apply_data_scope's
        # `kind == "all"` check returns the full queryset before the
        # model_type if/elif chain runs, so an unsupported model_type still
        # returns everything rather than falling through to .none().
        qs = apply_data_scope(self.superuser, Attendance.objects.all(), "not_a_real_model_type")
        ids = set(qs.values_list("id", flat=True))
        self.assertEqual(ids, {self.attendance_57.id, self.attendance_80.id, self.attendance_dropped.id})
