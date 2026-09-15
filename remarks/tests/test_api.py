from datetime import date
from django.contrib.auth.models import Group
from django.test import Client, TestCase
from rest_framework_simplejwt.tokens import RefreshToken
from course_offerings.models import CourseOffering
from courses.models import Course
from departments.models import Department
from enrollments.models import Enrollment
from remarks.models import Remark
from sections.models import Section
from students.models import Student
from teachers.models import Teacher
from users.models import User
from users.repositories.user_repository import UserRepository


# Exercises the actual HTTP views (not just remarks/authorization.py directly)
# to cover the permission fix: a teacher/student hitting /api/remarks/ used to
# get 403 "remarks.view_remark required" because the TEACHER/STUDENT groups
# were never granted the model permissions - see
# remarks/migrations/0002_grant_group_permissions.py.
class RemarkApiPermissionTests(TestCase):

    def setUp(self):
        self.department = Department.objects.create(name = "Computing", code = "CMP")
        self.section = Section.objects.create(
            name = "A", department = self.department, semester_number = 1, academic_year = 2026,
        )

        teacher_user = User.objects.create_user(
            email = "teacher@example.com", name = "Teacher A", password = "x", role = "teacher",
        )
        self.teacher = Teacher.objects.create(
            user = teacher_user, employee_id = "EMP-A", phone_number = "1234567",
            department = self.department, designation = "Lecturer", qualification = "MSc",
            date_of_joining = date(2020, 1, 1), salary = 1,
        )

        student_user = User.objects.create_user(
            email = "student@example.com", name = "Student 57", password = "x", role = "student",
        )
        self.student = Student.objects.create(
            user = student_user, parents_phone_number = "1234567",
            department = self.department, section = self.section,
        )

        # Real approval path (not a manual Group.objects.create) - the same
        # path a freshly-approved teacher/student account goes through, so
        # this test genuinely covers "does approve() leave the user able to
        # use the remarks feature".
        UserRepository().approve(teacher_user)
        UserRepository().approve(student_user)

        self.course = Course.objects.create(
            name = "Databases", code = "CS101", credits = 3, department = self.department, teacher = self.teacher,
        )
        self.offering = CourseOffering.objects.create(
            course = self.course, teacher = self.teacher, semester = CourseOffering.Semester.FALL,
            academic_year = 2026, section = self.section,
        )
        Enrollment.objects.create(student = self.student, course_offering = self.offering)

        self.remark = Remark.objects.create(
            student = self.student, teacher = self.teacher, course_offering = self.offering,
            remark_text = "Needs to work on joins.", visibility = Remark.Visibility.STUDENT_VISIBLE,
        )

        self.client = Client()

    def _auth_headers(self, user):
        token = str(RefreshToken.for_user(user).access_token)
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    def test_teacher_group_has_full_remark_permissions_after_migration(self):
        group = Group.objects.get(name = "TEACHER")
        codenames = set(group.permissions.values_list("codename", flat = True))
        self.assertTrue({"view_remark", "add_remark", "change_remark", "delete_remark"}.issubset(codenames))

    def test_student_group_has_view_only_remark_permission_after_migration(self):
        group = Group.objects.get(name = "STUDENT")
        codenames = set(group.permissions.values_list("codename", flat = True))
        self.assertIn("view_remark", codenames)
        self.assertNotIn("add_remark", codenames)

    def test_teacher_can_list_remarks_without_403(self):
        response = self.client.get("/api/remarks/", **self._auth_headers(self.teacher.user))
        self.assertEqual(response.status_code, 200)
        ids = {row["id"] for row in response.json()["results"]}
        self.assertIn(self.remark.id, ids)

    def test_student_can_list_own_remarks_without_403(self):
        response = self.client.get("/api/remarks/", **self._auth_headers(self.student.user))
        self.assertEqual(response.status_code, 200)
        remarks = {row["remark"] for row in response.json()["results"]}
        self.assertIn(self.remark.remark_text, remarks)

    def test_teacher_can_create_remark_end_to_end(self):
        response = self.client.post(
            "/api/remarks/",
            data = {
                "student": self.student.id,
                "course_offering": self.offering.id,
                "remark_text": "Great progress this week.",
                "visibility": "PRIVATE",
            },
            content_type = "application/json",
            **self._auth_headers(self.teacher.user),
        )
        self.assertEqual(response.status_code, 201)
