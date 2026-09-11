from datetime import date
from django.test import TestCase
from course_offerings.models import CourseOffering
from courses.models import Course
from departments.models import Department
from enrollments.models import Enrollment
from remarks.authorization import get_remarks_queryset_for_user, teacher_can_access_student_in_offering
from remarks.models import Remark
from sections.models import Section
from students.models import Student
from teachers.models import Teacher
from users.models import User


class RemarkAuthorizationTests(TestCase):

    def setUp(self):
        self.department = Department.objects.create(name = "Computing", code = "CMP")
        self.section = Section.objects.create(
            name = "A", department = self.department, semester_number = 1, academic_year = 2026,
        )

        def make_teacher(email, name, employee_id):
            user = User.objects.create_user(email = email, name = name, password = "x", role = "teacher")
            return Teacher.objects.create(
                user = user, employee_id = employee_id, phone_number = "1234567",
                department = self.department, designation = "Lecturer", qualification = "MSc",
                date_of_joining = date(2020, 1, 1), salary = 1,
            )

        def make_student(email, name):
            user = User.objects.create_user(email = email, name = name, password = "x", role = "student")
            return Student.objects.create(
                user = user, parents_phone_number = "1234567",
                department = self.department, section = self.section,
            )

        # Teacher A teaches CS101, teacher B teaches CS102 - two independent classes.
        self.teacher_a = make_teacher("teacher.a@example.com", "Teacher A", "EMP-A")
        self.teacher_b = make_teacher("teacher.b@example.com", "Teacher B", "EMP-B")

        self.course_a = Course.objects.create(name = "Databases", code = "CS101", credits = 3, department = self.department, teacher = self.teacher_a)
        self.course_b = Course.objects.create(name = "Networks", code = "CS102", credits = 3, department = self.department, teacher = self.teacher_b)

        self.offering_a = CourseOffering.objects.create(
            course = self.course_a, teacher = self.teacher_a, semester = CourseOffering.Semester.FALL,
            academic_year = 2026, section = self.section,
        )
        self.offering_b = CourseOffering.objects.create(
            course = self.course_b, teacher = self.teacher_b, semester = CourseOffering.Semester.FALL,
            academic_year = 2026, section = self.section,
        )

        # Student 57 is enrolled in teacher A's class only.
        self.student_57 = make_student("student57@example.com", "Student 57")
        Enrollment.objects.create(student = self.student_57, course_offering = self.offering_a)

        # Student 80 is enrolled in teacher B's class only - unrelated to teacher A.
        self.student_80 = make_student("student80@example.com", "Student 80")
        Enrollment.objects.create(student = self.student_80, course_offering = self.offering_b)

        self.private_remark = Remark.objects.create(
            student = self.student_57, teacher = self.teacher_a, course_offering = self.offering_a,
            remark_text = "Struggling with joins.", visibility = Remark.Visibility.PRIVATE,
        )
        self.visible_remark = Remark.objects.create(
            student = self.student_57, teacher = self.teacher_a, course_offering = self.offering_a,
            remark_text = "Improved significantly.", visibility = Remark.Visibility.STUDENT_VISIBLE,
        )

    # ── teacher_can_access_student_in_offering ──────────────────────────

    def test_teacher_can_access_own_student_in_own_offering(self):
        self.assertTrue(
            teacher_can_access_student_in_offering(self.teacher_a, self.student_57, self.offering_a)
        )

    def test_teacher_cannot_access_student_not_enrolled_in_their_offering(self):
        # Student 80 is not enrolled in offering_a at all.
        self.assertFalse(
            teacher_can_access_student_in_offering(self.teacher_a, self.student_80, self.offering_a)
        )

    def test_teacher_cannot_access_offering_they_do_not_teach(self):
        # Teacher A does not teach offering_b, even though student_80 is enrolled there.
        self.assertFalse(
            teacher_can_access_student_in_offering(self.teacher_a, self.student_80, self.offering_b)
        )

    def test_teacher_cannot_use_dropped_enrollment(self):
        Enrollment.objects.create(
            student = self.student_80, course_offering = self.offering_a, status = Enrollment.Status.DROPPED,
        )
        self.assertFalse(
            teacher_can_access_student_in_offering(self.teacher_a, self.student_80, self.offering_a)
        )

    # ── get_remarks_queryset_for_user: student role ─────────────────────

    def test_student_sees_only_their_own_student_visible_remarks(self):
        qs = get_remarks_queryset_for_user(self.student_57.user)
        ids = set(qs.values_list("id", flat = True))
        self.assertEqual(ids, {self.visible_remark.id})  # PRIVATE remark excluded

    def test_student_cannot_see_another_students_remarks_via_query_param(self):
        # Student 80 tries to request student 57's remarks by passing student=57.
        qs = get_remarks_queryset_for_user(self.student_80.user, student_id = self.student_57.id)
        self.assertEqual(qs.count(), 0)

    # ── get_remarks_queryset_for_user: teacher role ─────────────────────

    def test_teacher_sees_remarks_for_their_own_class(self):
        qs = get_remarks_queryset_for_user(self.teacher_a.user)
        ids = set(qs.values_list("id", flat = True))
        self.assertEqual(ids, {self.private_remark.id, self.visible_remark.id})

    def test_teacher_cannot_query_unauthorized_student(self):
        # Teacher A has no relationship to student 80.
        qs = get_remarks_queryset_for_user(self.teacher_a.user, student_id = self.student_80.id)
        self.assertEqual(qs.count(), 0)

    def test_teacher_b_does_not_see_teacher_a_remarks(self):
        qs = get_remarks_queryset_for_user(self.teacher_b.user)
        self.assertEqual(qs.count(), 0)
