"""
Phase 1 of the RAG effort: prove, with real ORM tests against the actual
database, that the existing authorization functions already provide a safe
data-scoping boundary for the academic-understanding data the AI assistant
will retrieve - attendance and teacher remarks first and foremost, plus the
course-offering/identity scope both depend on.

This file does NOT introduce any new authorization logic. It only calls:

    common.permissions.apply_data_scope(user, queryset, model_type)
    common.permissions.get_scope_identity(user)
    remarks.authorization.get_remarks_queryset_for_user(user, student_id=None)

against real fixtures and asserts on the IDs/querysets they return. No AI,
no pgvector, no new models, no API endpoints.

Assignments are intentionally out of scope here: the AI assistant's primary
purpose is academic-performance understanding via attendance (SQL
aggregation) and remarks (vector/semantic retrieval), not assignment
metadata - and assignment SUBMISSION evaluation was already separated out
as its own, later workflow. assignments.authorization is left untested by
this file; it can gain equivalent coverage later if/when assignments
actually become a retrieval source.
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
    Fixture mirrors the pattern used in remarks/tests/test_authorization.py
    and assignments/tests/test_api.py: two independent teacher/offering
    pairs, so cross-teacher and cross-student leakage is always checkable.
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

        # Teacher A teaches CS101 (offering_a), Teacher B teaches CS102 (offering_b) -
        # two fully independent classes, used to prove cross-teacher isolation.
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

        # Student 57 is actively enrolled in teacher A's class only.
        self.student_57 = make_student("student57@example.com", "Student 57")
        self.enrollment_57 = Enrollment.objects.create(
            student=self.student_57, course_offering=self.offering_a, status=Enrollment.Status.ACTIVE,
        )

        # Student 80 is actively enrolled in teacher B's class only - unrelated to teacher A.
        self.student_80 = make_student("student80@example.com", "Student 80")
        self.enrollment_80 = Enrollment.objects.create(
            student=self.student_80, course_offering=self.offering_b, status=Enrollment.Status.ACTIVE,
        )

        # Student "dropped" was enrolled in teacher A's class but has since dropped it -
        # used to document how apply_data_scope's "attendance" and "course_offering"
        # branches actually handle (or, as it turns out, do not filter on) DROPPED
        # enrollment status.
        self.student_dropped = make_student("dropped@example.com", "Dropped Student")
        self.enrollment_dropped = Enrollment.objects.create(
            student=self.student_dropped, course_offering=self.offering_a, status=Enrollment.Status.DROPPED,
        )

        # Remarks: one PRIVATE, one STUDENT_VISIBLE, both about student_57 in offering_a.
        self.private_remark = Remark.objects.create(
            student=self.student_57, teacher=self.teacher_a, course_offering=self.offering_a,
            remark_text="Struggling with joins.", visibility=Remark.Visibility.PRIVATE,
        )
        self.visible_remark = Remark.objects.create(
            student=self.student_57, teacher=self.teacher_a, course_offering=self.offering_a,
            remark_text="Improved significantly.", visibility=Remark.Visibility.STUDENT_VISIBLE,
        )

        # Attendance: one row per active enrollment.
        self.attendance_57 = Attendance.objects.create(
            enrollment=self.enrollment_57, date=date(2026, 2, 1), status=Attendance.Status.PRESENT,
        )
        self.attendance_80 = Attendance.objects.create(
            enrollment=self.enrollment_80, date=date(2026, 2, 1), status=Attendance.Status.ABSENT,
        )
        self.attendance_dropped = Attendance.objects.create(
            enrollment=self.enrollment_dropped, date=date(2026, 2, 1), status=Attendance.Status.ABSENT,
        )

        # Superuser - existing unrestricted ("all") behavior.
        self.superuser = User.objects.create_superuser(
            email="root@example.com", name="Root", password="x",
        )

        # role="admin" but NOT a Django superuser, and with neither a teacher_profile
        # nor a student_profile. Per common/permissions.py::get_scope_identity, this
        # resolves to kind "none" - an existing inconsistency we are explicitly
        # locking in as current behavior, not fixing, per Phase 1 scope.
        self.admin_non_superuser = User.objects.create_user(
            email="admin@example.com", name="Admin", password="x", role="admin",
        )

    # ── Remarks: student role ───────────────────────────────────────────

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

    # ── Remarks: teacher role ────────────────────────────────────────────

    def test_teacher_sees_remarks_for_their_own_offering_including_private(self):
        qs = get_remarks_queryset_for_user(self.teacher_a.user)
        ids = set(qs.values_list("id", flat=True))
        self.assertEqual(ids, {self.private_remark.id, self.visible_remark.id})

    def test_teacher_b_does_not_see_teacher_a_remarks(self):
        qs = get_remarks_queryset_for_user(self.teacher_b.user)
        self.assertEqual(qs.count(), 0)

    def test_teacher_probing_unauthorized_student_id_returns_empty(self):
        # Anti-enumeration: teacher_a has no relationship to student_80 at all.
        # get_remarks_queryset_for_user must return an empty queryset, not an
        # error and not an unfiltered one - this is the exact behavior already
        # proven in remarks/tests/test_authorization.py, re-asserted here
        # because Phase 2/7 retrieval will depend on it.
        qs = get_remarks_queryset_for_user(self.teacher_a.user, student_id=self.student_80.id)
        self.assertEqual(qs.count(), 0)

    # ── Attendance (via apply_data_scope) - the primary structured source ─

    def test_student_attendance_scope_contains_only_own_attendance(self):
        qs = apply_data_scope(self.student_57.user, Attendance.objects.all(), "attendance")
        ids = set(qs.values_list("id", flat=True))
        self.assertEqual(ids, {self.attendance_57.id})
        self.assertNotIn(self.attendance_80.id, ids)

    def test_teacher_attendance_scope_contains_only_own_offering_attendance(self):
        qs = apply_data_scope(self.teacher_a.user, Attendance.objects.all(), "attendance")
        ids = set(qs.values_list("id", flat=True))
        self.assertNotIn(self.attendance_80.id, ids)  # teacher_b's offering, must stay excluded
        self.assertIn(self.attendance_57.id, ids)

    def test_teacher_b_does_not_see_teacher_a_attendance(self):
        qs = apply_data_scope(self.teacher_b.user, Attendance.objects.all(), "attendance")
        ids = set(qs.values_list("id", flat=True))
        self.assertNotIn(self.attendance_57.id, ids)
        self.assertNotIn(self.attendance_dropped.id, ids)

    def test_attendance_scope_does_not_exclude_dropped_enrollments(self):
        # Documents ACTUAL current behavior, not a desired one: unlike
        # remarks/assignments authorization, apply_data_scope's "attendance"
        # branch filters only on enrollment__student / enrollment__course_
        # offering__teacher - there is no status__in=[ACTIVE, COMPLETED]
        # check. A DROPPED enrollment's attendance history therefore still
        # appears for both the student and their (former) teacher. This is
        # arguably correct for a historical attendance record, but it is a
        # real, pre-existing difference from how remarks/assignments treat
        # DROPPED status - flagged here for visibility, not "fixed" as part
        # of Phase 1.
        student_qs = apply_data_scope(self.student_dropped.user, Attendance.objects.all(), "attendance")
        self.assertIn(self.attendance_dropped.id, set(student_qs.values_list("id", flat=True)))

        teacher_qs = apply_data_scope(self.teacher_a.user, Attendance.objects.all(), "attendance")
        self.assertIn(self.attendance_dropped.id, set(teacher_qs.values_list("id", flat=True)))

    # ── Course offering scope (via apply_data_scope) ────────────────────

    def test_student_course_offering_scope_contains_only_authorized_offerings(self):
        qs = apply_data_scope(self.student_57.user, CourseOffering.objects.all(), "course_offering")
        ids = set(qs.values_list("id", flat=True))
        self.assertEqual(ids, {self.offering_a.id})

    def test_teacher_course_offering_scope_contains_only_taught_offerings(self):
        qs = apply_data_scope(self.teacher_a.user, CourseOffering.objects.all(), "course_offering")
        ids = set(qs.values_list("id", flat=True))
        self.assertEqual(ids, {self.offering_a.id})

    def test_course_offering_scope_does_not_exclude_dropped_enrollments(self):
        # Documents ACTUAL current behavior, not a desired one: unlike the
        # attendance and assignment branches, apply_data_scope's
        # "course_offering" branch filters only on enrollment EXISTENCE
        # (enrollments__student=user_student), with no status__in check.
        # A student whose only enrollment in an offering is DROPPED still
        # sees that offering through this specific scope. This is a real,
        # pre-existing inconsistency in common/permissions.py - flagged here
        # for visibility, intentionally NOT "fixed" as part of Phase 1.
        qs = apply_data_scope(self.student_dropped.user, CourseOffering.objects.all(), "course_offering")
        ids = set(qs.values_list("id", flat=True))
        self.assertEqual(ids, {self.offering_a.id})

    # ── Superuser: existing unrestricted "all" behavior ─────────────────

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

    # ── Anonymous / no-profile user ──────────────────────────────────────

    def test_anonymous_user_scope_identity_is_anon(self):
        kind, profile = get_scope_identity(AnonymousUser())
        self.assertEqual(kind, "anon")
        self.assertIsNone(profile)

    def test_anonymous_user_gets_no_attendance(self):
        qs = apply_data_scope(AnonymousUser(), Attendance.objects.all(), "attendance")
        self.assertEqual(qs.count(), 0)

    def test_anonymous_user_gets_no_remarks(self):
        # get_remarks_queryset_for_user does getattr(user, "teacher_profile"/"student_profile"),
        # both of which are simply absent on AnonymousUser, so it falls through
        # to Remark.objects.none() the same way a "none"-kind user would.
        qs = get_remarks_queryset_for_user(AnonymousUser())
        self.assertEqual(qs.count(), 0)

    # ── role="admin", non-superuser: existing behavior preserved ────────

    def test_role_admin_non_superuser_scope_identity_is_none(self):
        # Locks in the existing inconsistency discovered during the RAG
        # security review: a role="admin" user who is not also a Django
        # superuser has neither teacher_profile nor student_profile, so
        # get_scope_identity falls through to "none". This is current
        # behavior, not something Phase 1 changes.
        kind, profile = get_scope_identity(self.admin_non_superuser)
        self.assertEqual(kind, "none")
        self.assertIsNone(profile)

    def test_role_admin_non_superuser_gets_no_attendance(self):
        qs = apply_data_scope(self.admin_non_superuser, Attendance.objects.all(), "attendance")
        self.assertEqual(qs.count(), 0)

    def test_role_admin_non_superuser_gets_no_remarks(self):
        qs = get_remarks_queryset_for_user(self.admin_non_superuser)
        self.assertEqual(qs.count(), 0)

    # ── apply_data_scope: unsupported model_type ────────────────────────

    def test_unsupported_model_type_returns_empty_queryset(self):
        qs = apply_data_scope(self.student_57.user, Attendance.objects.all(), "not_a_real_model_type")
        self.assertEqual(qs.count(), 0)

    def test_superuser_bypasses_model_type_dispatch_entirely(self):
        # Documents actual behavior: apply_data_scope's `kind == "all"` check
        # returns the (soft-delete-filtered) queryset immediately, BEFORE the
        # model_type if/elif chain runs at all. So for a superuser, model_type
        # is not validated or even consulted - an unsupported/garbage
        # model_type still returns the full queryset, unlike every other
        # role, where an unsupported model_type falls through to .none().
        # This is current behavior; Phase 1 does not change it.
        qs = apply_data_scope(self.superuser, Attendance.objects.all(), "not_a_real_model_type")
        ids = set(qs.values_list("id", flat=True))
        self.assertEqual(ids, {self.attendance_57.id, self.attendance_80.id, self.attendance_dropped.id})
