from datetime import date, timedelta
from django.test import Client, TestCase
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken
from course_offerings.models import CourseOffering
from courses.models import Course
from departments.models import Department
from enrollments.models import Enrollment
from assignments.models import Assignment, Submission
from sections.models import Section
from students.models import Student
from teachers.models import Teacher
from users.models import User
from users.repositories.user_repository import UserRepository


class AssignmentApiTests(TestCase):

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

        def make_student(email, name):
            user = User.objects.create_user(email = email, name = name, password = "x", role = "student")
            UserRepository().approve(user)
            return Student.objects.create(
                user = user, parents_phone_number = "1234567",
                department = self.department, section = self.section,
            )

        self.teacher_a = make_teacher("teacher.a@example.com", "Teacher A", "EMP-A")
        self.teacher_b = make_teacher("teacher.b@example.com", "Teacher B", "EMP-B")

        self.course = Course.objects.create(
            name = "Databases", code = "CS101", credits = 3, department = self.department, teacher = self.teacher_a,
        )
        self.offering = CourseOffering.objects.create(
            course = self.course, teacher = self.teacher_a, semester = CourseOffering.Semester.FALL,
            academic_year = 2026, section = self.section,
        )

        self.other_course = Course.objects.create(
            name = "Networks", code = "CS102", credits = 3, department = self.department, teacher = self.teacher_b,
        )
        self.other_offering = CourseOffering.objects.create(
            course = self.other_course, teacher = self.teacher_b, semester = CourseOffering.Semester.FALL,
            academic_year = 2026, section = self.section,
        )

        self.student_enrolled = make_student("enrolled@example.com", "Enrolled Student")
        self.student_other = make_student("other@example.com", "Other Student")
        Enrollment.objects.create(student = self.student_enrolled, course_offering = self.offering)
        Enrollment.objects.create(student = self.student_other, course_offering = self.other_offering)

        self.future_due = timezone.now() + timedelta(days = 7)
        self.assignment = Assignment.objects.create(
            course_offering = self.offering, teacher = self.teacher_a,
            title = "SQL Joins", description = "Do the joins.", due_at = self.future_due,
        )

        self.client = Client()

    def _auth_headers(self, user):
        token = str(RefreshToken.for_user(user).access_token)
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    # ── Teacher CRUD + authorization ────────────────────────────────────

    def test_teacher_can_create_assignment_for_own_offering(self):
        response = self.client.post(
            "/api/assignments/",
            data = {
                "course_offering": self.offering.id,
                "title": "New Assignment",
                "description": "Instructions",
                "due_at": self.future_due.isoformat(),
            },
            content_type = "application/json",
            **self._auth_headers(self.teacher_a.user),
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(set(response.json().keys()), {"id", "title", "description", "due_at", "attachment_url"})

    def test_teacher_cannot_create_assignment_for_offering_they_do_not_teach(self):
        response = self.client.post(
            "/api/assignments/",
            data = {
                "course_offering": self.other_offering.id,
                "title": "New Assignment",
                "due_at": self.future_due.isoformat(),
            },
            content_type = "application/json",
            **self._auth_headers(self.teacher_a.user),
        )
        self.assertEqual(response.status_code, 403)

    def test_teacher_list_scoped_to_own_offerings_with_minimal_fields(self):
        response = self.client.get("/api/assignments/", **self._auth_headers(self.teacher_a.user))
        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(set(results[0].keys()), {"id", "title", "due_at", "submitted_count", "pending_count"})
        self.assertEqual(results[0]["submitted_count"], 0)
        self.assertEqual(results[0]["pending_count"], 1)

    def test_teacher_list_result_rows_never_contain_a_nested_course_object(self):
        # Guards against course context being duplicated into every row - it
        # must appear exactly once, as the envelope's own top-level "course",
        # never repeated inside each assignment.
        response = self.client.get(
            f"/api/assignments/?course_offering={self.offering.id}", **self._auth_headers(self.teacher_a.user)
        )
        self.assertEqual(response.status_code, 200)
        for row in response.json()["results"]:
            self.assertNotIn("course", row)
            self.assertNotIn("course_name", row)
            self.assertNotIn("course_code", row)
            self.assertNotIn("section_name", row)

    def test_teacher_list_includes_course_summary_when_scoped_to_an_offering(self):
        # Lets the teacher's Assignments page render its "Maths (1010) - D"
        # header without fetching the whole /teachers/me/courses/ list.
        response = self.client.get(
            f"/api/assignments/?course_offering={self.offering.id}", **self._auth_headers(self.teacher_a.user)
        )
        self.assertEqual(response.status_code, 200)
        course = response.json()["course"]
        self.assertEqual(set(course.keys()), {"id", "course_name", "course_code", "section_name"})
        self.assertEqual(course["id"], self.offering.id)
        self.assertEqual(course["course_code"], "CS101")

    def test_course_summary_absent_without_course_offering_filter(self):
        response = self.client.get("/api/assignments/", **self._auth_headers(self.teacher_a.user))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("course", response.json())

    def test_course_summary_not_returned_for_offering_teacher_does_not_teach(self):
        response = self.client.get(
            f"/api/assignments/?course_offering={self.other_offering.id}", **self._auth_headers(self.teacher_a.user)
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("course", response.json())
        self.assertEqual(response.json()["results"], [])

    def test_teacher_b_does_not_see_teacher_a_assignment(self):
        response = self.client.get("/api/assignments/", **self._auth_headers(self.teacher_b.user))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["results"], [])

    def test_teacher_b_cannot_update_teacher_a_assignment(self):
        response = self.client.patch(
            f"/api/assignments/{self.assignment.id}/",
            data = {"title": "Hacked"},
            content_type = "application/json",
            **self._auth_headers(self.teacher_b.user),
        )
        self.assertEqual(response.status_code, 403)

    def test_teacher_b_cannot_delete_teacher_a_assignment(self):
        response = self.client.delete(f"/api/assignments/{self.assignment.id}/", **self._auth_headers(self.teacher_b.user))
        self.assertEqual(response.status_code, 403)

    def test_teacher_b_cannot_view_teacher_a_submissions_roster(self):
        response = self.client.get(f"/api/assignments/{self.assignment.id}/submissions/", **self._auth_headers(self.teacher_b.user))
        self.assertEqual(response.status_code, 403)

    # ── Student access ───────────────────────────────────────────────────

    def test_enrolled_student_can_see_assignment(self):
        response = self.client.get("/api/assignments/", **self._auth_headers(self.student_enrolled.user))
        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(
            set(results[0].keys()),
            {"id", "title", "description", "due_at", "attachment_url", "course_name", "course_code", "status", "submitted_at"},
        )
        self.assertEqual(results[0]["status"], "PENDING")

    def test_non_enrolled_student_cannot_see_assignment(self):
        response = self.client.get("/api/assignments/", **self._auth_headers(self.student_other.user))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["results"], [])

    def test_non_enrolled_student_cannot_access_assignment_detail(self):
        response = self.client.get(f"/api/assignments/{self.assignment.id}/", **self._auth_headers(self.student_other.user))
        self.assertEqual(response.status_code, 404)

    def test_non_enrolled_student_cannot_fetch_own_submission_status(self):
        response = self.client.get(
            f"/api/assignments/{self.assignment.id}/submission/", **self._auth_headers(self.student_other.user)
        )
        self.assertEqual(response.status_code, 403)


class SubmissionApiTests(TestCase):

    def setUp(self):
        self.department = Department.objects.create(name = "Computing", code = "CMP")
        self.section = Section.objects.create(
            name = "A", department = self.department, semester_number = 1, academic_year = 2026,
        )

        teacher_user = User.objects.create_user(email = "t@example.com", name = "Teacher", password = "x", role = "teacher")
        UserRepository().approve(teacher_user)
        self.teacher = Teacher.objects.create(
            user = teacher_user, employee_id = "EMP-A", phone_number = "1234567",
            department = self.department, designation = "Lecturer", qualification = "MSc",
            date_of_joining = date(2020, 1, 1), salary = 1,
        )

        def make_student(email, name):
            user = User.objects.create_user(email = email, name = name, password = "x", role = "student")
            UserRepository().approve(user)
            return Student.objects.create(
                user = user, parents_phone_number = "1234567",
                department = self.department, section = self.section,
            )

        self.student_a = make_student("a@example.com", "Alice")
        self.student_b = make_student("b@example.com", "Bob")

        self.course = Course.objects.create(
            name = "Databases", code = "CS101", credits = 3, department = self.department, teacher = self.teacher,
        )
        self.offering = CourseOffering.objects.create(
            course = self.course, teacher = self.teacher, semester = CourseOffering.Semester.FALL,
            academic_year = 2026, section = self.section,
        )
        Enrollment.objects.create(student = self.student_a, course_offering = self.offering)
        Enrollment.objects.create(student = self.student_b, course_offering = self.offering)

        self.assignment = Assignment.objects.create(
            course_offering = self.offering, teacher = self.teacher,
            title = "SQL Joins", due_at = timezone.now() + timedelta(days = 7),
        )

        self.submission_a = Submission.objects.create(
            assignment = self.assignment, student = self.student_a, file_key = "submissions/1/1/file.pdf",
        )

        self.client = Client()

    def _auth_headers(self, user):
        token = str(RefreshToken.for_user(user).access_token)
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    def test_student_can_see_own_submission_status(self):
        response = self.client.get(
            f"/api/assignments/{self.assignment.id}/submission/", **self._auth_headers(self.student_a.user)
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "SUBMITTED")

    def test_student_b_sees_pending_not_student_a_submission(self):
        response = self.client.get(
            f"/api/assignments/{self.assignment.id}/submission/", **self._auth_headers(self.student_b.user)
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "PENDING")

    def test_teacher_roster_shows_both_students_with_correct_status(self):
        response = self.client.get(
            f"/api/assignments/{self.assignment.id}/submissions/", **self._auth_headers(self.teacher.user)
        )
        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        by_id = {r["student_id"]: r for r in results}
        self.assertEqual(by_id[self.student_a.id]["status"], "SUBMITTED")
        self.assertEqual(by_id[self.student_b.id]["status"], "PENDING")
        self.assertIsNotNone(by_id[self.student_a.id]["file_url"])
        self.assertIsNone(by_id[self.student_b.id]["file_url"])
        self.assertEqual(
            set(by_id[self.student_a.id].keys()), {"student_id", "student_name", "status", "submitted_at", "file_url"}
        )

    def test_teacher_roster_uses_standard_pagination_envelope(self):
        response = self.client.get(
            f"/api/assignments/{self.assignment.id}/submissions/", **self._auth_headers(self.teacher.user)
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(set(data.keys()), {"total_count", "current_page", "page_size", "total_pages", "results"})
        self.assertEqual(data["total_count"], 2)
        self.assertEqual(data["page_size"], 10)
        self.assertEqual(data["current_page"], 1)
        self.assertEqual(data["total_pages"], 1)

    def test_teacher_roster_paginates_with_page_size(self):
        # 2 existing enrollments (Alice, Bob) + 9 more = 11, to force a second page.
        for i in range(9):
            student = Student.objects.create(
                user = User.objects.create_user(
                    email = f"extra{i}@example.com", name = f"Extra {i}", password = "x", role = "student",
                ),
                parents_phone_number = "1234567", department = self.department, section = self.section,
            )
            Enrollment.objects.create(student = student, course_offering = self.offering)

        response = self.client.get(
            f"/api/assignments/{self.assignment.id}/submissions/?page=1&page_size=10",
            **self._auth_headers(self.teacher.user),
        )
        data = response.json()
        self.assertEqual(data["total_count"], 11)
        self.assertEqual(len(data["results"]), 10)
        self.assertEqual(data["total_pages"], 2)

        response2 = self.client.get(
            f"/api/assignments/{self.assignment.id}/submissions/?page=2&page_size=10",
            **self._auth_headers(self.teacher.user),
        )
        data2 = response2.json()
        self.assertEqual(len(data2["results"]), 1)
        self.assertEqual(data2["current_page"], 2)
