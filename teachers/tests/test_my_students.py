from datetime import date
from django.test import Client, TestCase
from rest_framework_simplejwt.tokens import RefreshToken
from course_offerings.models import CourseOffering
from courses.models import Course
from departments.models import Department
from enrollments.models import Enrollment
from sections.models import Section
from students.models import Student
from teachers.models import Teacher
from users.models import User
from users.repositories.user_repository import UserRepository


class MyTeacherStudentsApiTests(TestCase):

    def setUp(self):
        self.department = Department.objects.create(name = "Computing", code = "CMP")
        self.section = Section.objects.create(
            name = "A", department = self.department, semester_number = 1, academic_year = 2026,
        )

        def make_teacher(email, name, employee_id):
            user = User.objects.create_user(email = email, name = name, password = "x", role = "teacher")
            UserRepository().approve(user)
            return Teacher.objects.create(
                user = user, employee_id = employee_id, phone_number = "1234567",
                department = self.department, designation = "Lecturer", qualification = "MSc",
                date_of_joining = date(2020, 1, 1), salary = 1,
            )

        self.teacher_a = make_teacher("a@example.com", "Teacher A", "EMP-A")
        self.teacher_b = make_teacher("b@example.com", "Teacher B", "EMP-B")

        self.course_a = Course.objects.create(
            name = "Maths", code = "MTH101", credits = 3, department = self.department, teacher = self.teacher_a,
        )
        self.offering_a = CourseOffering.objects.create(
            course = self.course_a, teacher = self.teacher_a, semester = CourseOffering.Semester.FALL,
            academic_year = 2026, section = self.section,
        )

        self.course_b = Course.objects.create(
            name = "English", code = "ENG101", credits = 3, department = self.department, teacher = self.teacher_b,
        )
        self.offering_b = CourseOffering.objects.create(
            course = self.course_b, teacher = self.teacher_b, semester = CourseOffering.Semester.FALL,
            academic_year = 2026, section = self.section,
        )

        self.student_a = self.make_student("sa@example.com", "Student A")
        self.student_b = self.make_student("sb@example.com", "Student B")
        Enrollment.objects.create(student = self.student_a, course_offering = self.offering_a)
        Enrollment.objects.create(student = self.student_b, course_offering = self.offering_b)

        self.client = Client()

    def make_student(self, email, name):
        user = User.objects.create_user(email = email, name = name, password = "x", role = "student")
        UserRepository().approve(user)
        return Student.objects.create(
            user = user, parents_phone_number = "1234567",
            department = self.department, section = self.section,
        )

    def _auth_headers(self, user):
        token = str(RefreshToken.for_user(user).access_token)
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    def test_course_offering_filter_returns_only_that_classs_students(self):
        response = self.client.get(
            f"/api/teachers/me/students/?course_offering_id={self.offering_a.id}",
            **self._auth_headers(self.teacher_a.user),
        )
        self.assertEqual(response.status_code, 200)
        names = {row["student_name"] for row in response.json()["results"]}
        self.assertEqual(names, {"Student A"})

    def test_teacher_cannot_access_another_teachers_offering_students(self):
        # teacher_a passing teacher_b's offering id must not leak teacher_b's
        # student - apply_data_scope restricts to teacher_a's own offerings
        # first, so this combination matches nothing.
        response = self.client.get(
            f"/api/teachers/me/students/?course_offering_id={self.offering_b.id}",
            **self._auth_headers(self.teacher_a.user),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["results"], [])

    def test_students_are_sorted_alphabetically_by_name(self):
        # Enrolled in reverse-alphabetical creation order, on purpose - the
        # response must still come back A-Z, same as Admin's Enrollments list
        # (reused ORDERING_FIELDS/DEFAULT_ORDERING = "name"), not DB insertion order.
        zara = self.make_student("z@example.com", "Zara Khan")
        amir = self.make_student("m@example.com", "Amir Baig")
        Enrollment.objects.create(student = zara, course_offering = self.offering_a)
        Enrollment.objects.create(student = amir, course_offering = self.offering_a)

        response = self.client.get(
            f"/api/teachers/me/students/?course_offering_id={self.offering_a.id}&page_size=10",
            **self._auth_headers(self.teacher_a.user),
        )
        names = [row["student_name"] for row in response.json()["results"]]
        self.assertEqual(names, sorted(names))
        self.assertEqual(names, ["Amir Baig", "Student A", "Zara Khan"])

    def test_response_row_keys_are_minimal(self):
        response = self.client.get(
            f"/api/teachers/me/students/?course_offering_id={self.offering_a.id}",
            **self._auth_headers(self.teacher_a.user),
        )
        row = response.json()["results"][0]
        self.assertEqual(
            set(row.keys()),
            {"enrollment_id", "student_id", "student_name", "student_email", "status", "profile_picture_url"},
        )
