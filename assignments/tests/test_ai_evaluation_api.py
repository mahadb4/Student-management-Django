"""
Phase 11B tests: POST .../ai-check/ and PATCH .../evaluation/.

No real Gemini API calls anywhere - AssignmentEvaluationService is patched
at its import site in ai_evaluation_api. No test in this file requires a
real GEMINI_API_KEY. S3Service.get_object_bytes is also patched so no real
S3 call happens either.
"""
import json
from datetime import date, timedelta
from unittest.mock import patch

from django.test import Client, TestCase
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from assignments.models import Assignment, AssignmentEvaluation, Submission
from assignments.services.assignment_evaluation_service import (
    AssignmentEvaluationError,
    AssignmentEvaluationResult,
)
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

SAMPLE_RESULT = AssignmentEvaluationResult(
    suggested_score=82,
    strengths=["Correct REST endpoints", "Clear code structure"],
    weaknesses=["Missing pagination"],
    feedback="Solid overall, missing a couple of requirements.",
    confidence="medium",
)


class _FakeEvaluationService:
    def __init__(self, *a, **k):
        pass

    def evaluate(self, evaluation_input):
        return SAMPLE_RESULT


class _FailingEvaluationService:
    def __init__(self, *a, **k):
        pass

    def evaluate(self, evaluation_input):
        raise AssignmentEvaluationError("Gemini evaluation request failed: RuntimeError")


class AiEvaluationApiTests(TestCase):

    def setUp(self):
        self.department = Department.objects.create(name="Computing", code="CMP")
        self.section = Section.objects.create(
            name="A", department=self.department, semester_number=1, academic_year=2026,
        )

        def make_teacher(email, name, employee_id):
            user = User.objects.create_user(email=email, name=name, password="x", role="teacher")
            UserRepository().approve(user)
            return Teacher.objects.create(
                user=user, employee_id=employee_id, phone_number="1234567",
                department=self.department, designation="Lecturer", qualification="MSc",
                date_of_joining=date(2020, 1, 1), salary=1,
            )

        def make_student(email, name):
            user = User.objects.create_user(email=email, name=name, password="x", role="student")
            UserRepository().approve(user)
            return Student.objects.create(
                user=user, parents_phone_number="1234567",
                department=self.department, section=self.section, placement_confirmed=True,
            )

        self.teacher_a = make_teacher("teacher.a@example.com", "Teacher A", "EMP-A")
        self.teacher_b = make_teacher("teacher.b@example.com", "Teacher B", "EMP-B")

        self.course = Course.objects.create(
            name="Databases", code="CS101", credits=3, department=self.department, teacher=self.teacher_a,
        )
        self.offering = CourseOffering.objects.create(
            course=self.course, teacher=self.teacher_a, semester=CourseOffering.Semester.FALL,
            academic_year=2026, section=self.section,
        )

        self.student = make_student("student@example.com", "Student One")
        Enrollment.objects.create(student=self.student, course_offering=self.offering)

        self.assignment = Assignment.objects.create(
            course_offering=self.offering, teacher=self.teacher_a,
            title="FOP #1", description="Build a Django REST API with auth, CRUD, and pagination.",
            due_at=timezone.now() + timedelta(days=7),
        )

        self.pdf_submission = Submission.objects.create(
            assignment=self.assignment, student=self.student,
            file_key=f"submissions/{self.assignment.id}/{self.student.id}/file.pdf",
        )

        self.client = Client()

    def _auth_headers(self, user):
        token = str(RefreshToken.for_user(user).access_token)
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    def _ai_check_url(self, assignment_id=None, student_id=None):
        return f"/api/assignments/{assignment_id or self.assignment.id}/submissions/{student_id or self.student.id}/ai-check/"

    def _evaluation_url(self, assignment_id=None, student_id=None):
        return f"/api/assignments/{assignment_id or self.assignment.id}/submissions/{student_id or self.student.id}/evaluation/"

    def _post_ai_check(self, user, assignment_id=None, student_id=None):
        return self.client.post(
            self._ai_check_url(assignment_id, student_id), content_type="application/json",
            **self._auth_headers(user),
        )

    # ── Security order ───────────────────────────────────────────────────

    def test_unauthenticated_request_is_rejected(self):
        response = self.client.post(self._ai_check_url(), content_type="application/json")
        self.assertEqual(response.status_code, 401)

    def test_non_teacher_caller_is_rejected(self):
        response = self._post_ai_check(self.student.user)
        self.assertEqual(response.status_code, 400)

    def test_teacher_cannot_ai_check_another_teachers_assignment(self):
        response = self._post_ai_check(self.teacher_b.user)
        self.assertEqual(response.status_code, 403)

    def test_nonexistent_assignment_returns_404(self):
        response = self._post_ai_check(self.teacher_a.user, assignment_id=999999)
        self.assertEqual(response.status_code, 404)

    def test_missing_submission_returns_404(self):
        other_student_user = User.objects.create_user(
            email="nosubmission@example.com", name="No Submission", password="x", role="student",
        )
        UserRepository().approve(other_student_user)
        no_submission_student = Student.objects.create(
            user=other_student_user, parents_phone_number="1234567",
            department=self.department, section=self.section,
        )
        response = self._post_ai_check(self.teacher_a.user, student_id=no_submission_student.id)
        self.assertEqual(response.status_code, 404)

    @patch("assignments.api.ai_evaluation_api.s3_service")
    def test_authorization_checked_before_any_s3_call(self, mock_s3):
        # teacher_b doesn't own this assignment - S3 must never be touched.
        self._post_ai_check(self.teacher_b.user)
        mock_s3.get_object_bytes.assert_not_called()

    # ── Format check (PDF only, V1) ─────────────────────────────────────

    @patch("assignments.api.ai_evaluation_api.s3_service")
    def test_non_pdf_submission_rejected_without_touching_s3_or_gemini(self, mock_s3):
        docx_submission = Submission.objects.create(
            assignment=self.assignment,
            student=Student.objects.create(
                user=User.objects.create_user(email="docx@example.com", name="Docx Student", password="x", role="student"),
                parents_phone_number="1234567", department=self.department, section=self.section,
            ),
            file_key=f"submissions/{self.assignment.id}/999/file.docx",
        )
        Enrollment.objects.create(student=docx_submission.student, course_offering=self.offering)

        with patch("assignments.api.ai_evaluation_api.AssignmentEvaluationService") as mock_service_cls:
            response = self._post_ai_check(self.teacher_a.user, student_id=docx_submission.student_id)

        self.assertEqual(response.status_code, 400)
        mock_s3.get_object_bytes.assert_not_called()
        mock_service_cls.assert_not_called()

    # ── Successful evaluation ────────────────────────────────────────────

    @patch("assignments.api.ai_evaluation_api.AssignmentEvaluationService", _FakeEvaluationService)
    @patch("assignments.api.ai_evaluation_api.s3_service")
    def test_successful_ai_check_creates_evaluation_with_expected_fields(self, mock_s3):
        mock_s3.get_object_bytes.return_value = b"%PDF-1.4 fake bytes"

        response = self._post_ai_check(self.teacher_a.user)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["suggested_score"], 82)
        self.assertEqual(data["strengths"], ["Correct REST endpoints", "Clear code structure"])
        self.assertEqual(data["status"], "AI_SUGGESTED")
        self.assertIsNone(data["final_score"])
        self.assertEqual(data["teacher_feedback"], "")

        mock_s3.get_object_bytes.assert_called_once_with(self.pdf_submission.file_key)

    @patch("assignments.api.ai_evaluation_api.AssignmentEvaluationService", _FakeEvaluationService)
    @patch("assignments.api.ai_evaluation_api.s3_service")
    def test_rerunning_ai_check_updates_same_row_not_duplicate(self, mock_s3):
        mock_s3.get_object_bytes.return_value = b"%PDF-1.4 fake bytes"

        self._post_ai_check(self.teacher_a.user)
        self._post_ai_check(self.teacher_a.user)

        self.assertEqual(AssignmentEvaluation.objects.filter(submission=self.pdf_submission).count(), 1)

    @patch("assignments.api.ai_evaluation_api.AssignmentEvaluationService", _FakeEvaluationService)
    @patch("assignments.api.ai_evaluation_api.s3_service")
    def test_s3_key_and_url_never_appear_in_response(self, mock_s3):
        mock_s3.get_object_bytes.return_value = b"%PDF-1.4 fake bytes"

        response = self._post_ai_check(self.teacher_a.user)

        body = response.content.decode()
        self.assertNotIn(self.pdf_submission.file_key, body)
        self.assertNotIn("s3.amazonaws.com", body)

    @patch("assignments.api.ai_evaluation_api.AssignmentEvaluationService", _FakeEvaluationService)
    @patch("assignments.api.ai_evaluation_api.s3_service")
    def test_no_remark_is_ever_automatically_created(self, mock_s3):
        mock_s3.get_object_bytes.return_value = b"%PDF-1.4 fake bytes"

        self._post_ai_check(self.teacher_a.user)

        self.assertEqual(Remark.objects.count(), 0)

    @patch("assignments.api.ai_evaluation_api.AssignmentEvaluationService", _FakeEvaluationService)
    @patch("assignments.api.ai_evaluation_api.s3_service")
    def test_no_final_grade_is_ever_automatically_set(self, mock_s3):
        mock_s3.get_object_bytes.return_value = b"%PDF-1.4 fake bytes"

        self._post_ai_check(self.teacher_a.user)

        evaluation = AssignmentEvaluation.objects.get(submission=self.pdf_submission)
        self.assertIsNone(evaluation.final_score)
        self.assertNotEqual(evaluation.status, AssignmentEvaluation.Status.APPROVED)

    # ── Failure handling ─────────────────────────────────────────────────

    @patch("assignments.api.ai_evaluation_api.AssignmentEvaluationService", _FailingEvaluationService)
    @patch("assignments.api.ai_evaluation_api.s3_service")
    def test_gemini_failure_produces_controlled_error_and_saves_nothing(self, mock_s3):
        mock_s3.get_object_bytes.return_value = b"%PDF-1.4 fake bytes"

        response = self._post_ai_check(self.teacher_a.user)

        self.assertEqual(response.status_code, 503)
        self.assertNotIn("RuntimeError", response.json()["error"])
        self.assertEqual(AssignmentEvaluation.objects.filter(submission=self.pdf_submission).count(), 0)

    def test_wrong_http_method_rejected(self):
        response = self.client.get(self._ai_check_url(), **self._auth_headers(self.teacher_a.user))
        self.assertEqual(response.status_code, 405)


class EvaluationReviewApiTests(TestCase):
    """Phase 11B: PATCH .../evaluation/ - the mandatory teacher-approval step."""

    def setUp(self):
        self.department = Department.objects.create(name="Computing", code="CMP")
        self.section = Section.objects.create(
            name="A", department=self.department, semester_number=1, academic_year=2026,
        )

        teacher_user = User.objects.create_user(email="t@example.com", name="Teacher", password="x", role="teacher")
        UserRepository().approve(teacher_user)
        self.teacher = Teacher.objects.create(
            user=teacher_user, employee_id="EMP-A", phone_number="1234567",
            department=self.department, designation="Lecturer", qualification="MSc",
            date_of_joining=date(2020, 1, 1), salary=1,
        )

        other_teacher_user = User.objects.create_user(email="t2@example.com", name="Teacher B", password="x", role="teacher")
        UserRepository().approve(other_teacher_user)
        self.other_teacher = Teacher.objects.create(
            user=other_teacher_user, employee_id="EMP-B", phone_number="1234567",
            department=self.department, designation="Lecturer", qualification="MSc",
            date_of_joining=date(2020, 1, 1), salary=1,
        )

        student_user = User.objects.create_user(email="s@example.com", name="Student", password="x", role="student")
        UserRepository().approve(student_user)
        self.student = Student.objects.create(
            user=student_user, parents_phone_number="1234567",
            department=self.department, section=self.section, placement_confirmed=True,
        )

        self.course = Course.objects.create(
            name="Databases", code="CS101", credits=3, department=self.department, teacher=self.teacher,
        )
        self.offering = CourseOffering.objects.create(
            course=self.course, teacher=self.teacher, semester=CourseOffering.Semester.FALL,
            academic_year=2026, section=self.section,
        )
        Enrollment.objects.create(student=self.student, course_offering=self.offering)

        self.assignment = Assignment.objects.create(
            course_offering=self.offering, teacher=self.teacher, title="FOP #1", description="...",
            due_at=timezone.now() + timedelta(days=7),
        )
        self.submission = Submission.objects.create(
            assignment=self.assignment, student=self.student,
            file_key=f"submissions/{self.assignment.id}/{self.student.id}/file.pdf",
        )
        self.evaluation = AssignmentEvaluation.objects.create(
            submission=self.submission, suggested_score=82,
            strengths=["Good structure"], weaknesses=["Missing pagination"],
            ai_feedback="Solid overall.", confidence="medium",
        )

        self.client = Client()

    def _auth_headers(self, user):
        token = str(RefreshToken.for_user(user).access_token)
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    def _url(self):
        return f"/api/assignments/{self.assignment.id}/submissions/{self.student.id}/evaluation/"

    def _patch(self, user, body):
        return self.client.patch(
            self._url(), data=json.dumps(body), content_type="application/json", **self._auth_headers(user),
        )

    def test_teacher_can_approve_with_the_ai_suggested_score(self):
        response = self._patch(self.teacher.user, {"status": "APPROVED", "final_score": 82, "teacher_feedback": "Agreed."})
        self.assertEqual(response.status_code, 200)
        self.evaluation.refresh_from_db()
        self.assertEqual(self.evaluation.final_score, 82)
        self.assertEqual(self.evaluation.status, "APPROVED")

    def test_teacher_can_edit_the_score_before_approving(self):
        response = self._patch(self.teacher.user, {"status": "EDITED", "final_score": 68, "teacher_feedback": "Lowered for missing error handling."})
        self.assertEqual(response.status_code, 200)
        self.evaluation.refresh_from_db()
        self.assertEqual(self.evaluation.final_score, 68)
        self.assertNotEqual(self.evaluation.final_score, self.evaluation.suggested_score)

    def test_teacher_can_reject_without_a_score(self):
        response = self._patch(self.teacher.user, {"status": "REJECTED"})
        self.assertEqual(response.status_code, 200)
        self.evaluation.refresh_from_db()
        self.assertEqual(self.evaluation.status, "REJECTED")
        self.assertIsNone(self.evaluation.final_score)

    def test_approve_requires_a_score(self):
        response = self._patch(self.teacher.user, {"status": "APPROVED"})
        self.assertEqual(response.status_code, 400)

    def test_score_out_of_range_rejected(self):
        response = self._patch(self.teacher.user, {"status": "APPROVED", "final_score": 150})
        self.assertEqual(response.status_code, 400)

    def test_negative_score_rejected(self):
        response = self._patch(self.teacher.user, {"status": "APPROVED", "final_score": -5})
        self.assertEqual(response.status_code, 400)

    def test_invalid_status_rejected(self):
        response = self._patch(self.teacher.user, {"status": "MAYBE", "final_score": 80})
        self.assertEqual(response.status_code, 400)

    def test_ai_suggested_status_cannot_be_set_via_review_endpoint(self):
        # AI_SUGGESTED is not a valid teacher-chosen status - only the AI
        # Check endpoint itself sets that state.
        response = self._patch(self.teacher.user, {"status": "AI_SUGGESTED", "final_score": 80})
        self.assertEqual(response.status_code, 400)

    def test_another_teacher_cannot_review_this_evaluation(self):
        response = self._patch(self.other_teacher.user, {"status": "APPROVED", "final_score": 80})
        self.assertEqual(response.status_code, 403)

    def test_suggested_fields_are_never_modified_by_review(self):
        self._patch(self.teacher.user, {"status": "EDITED", "final_score": 68, "teacher_feedback": "..."})
        self.evaluation.refresh_from_db()
        self.assertEqual(self.evaluation.suggested_score, 82)
        self.assertEqual(self.evaluation.strengths, ["Good structure"])
