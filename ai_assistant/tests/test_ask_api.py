"""
Tests for POST /api/ai-assistant/ask/. No real Gemini API calls anywhere -
the embedding service used inside semantic retrieval and the generation
service used by the orchestrator are both patched at their import sites.
"""
import json
import math
from datetime import date, timedelta
from unittest.mock import patch

from django.test import Client, TestCase
from django.conf import settings
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from ai_assistant.models import RemarkEmbedding
from ai_assistant.services.gemini_generation_service import AnswerGenerationError
from assignments.models import Assignment, Submission
from attendance.models import Attendance
from course_offerings.models import CourseOffering
from courses.models import Course
from departments.models import Department
from enrollments.models import Enrollment
from remarks.models import Remark
from sections.models import Section
from students.models import Student
from teachers.models import Teacher
from users.models import User

DIM = 768
URL = "/api/ai-assistant/ask/"


def _vector(angle_degrees):
    theta = math.radians(angle_degrees)
    return [math.cos(theta), math.sin(theta)] + [0.0] * (DIM - 2)


class _FakeEmbeddingModels:
    def __init__(self, values):
        self._values = values

    def embed_content(self, **kwargs):
        class _Obj:
            def __init__(self, values):
                self.values = values

        class _Result:
            def __init__(self, values):
                self.embeddings = [_Obj(values)]

        return _Result(self._values)


class _FakeEmbeddingClient:
    def __init__(self, values):
        self.models = _FakeEmbeddingModels(values)


class _FakeGeminiEmbeddingService:
    """Injected in place of ai_assistant.retrieval.semantic_remarks.GeminiEmbeddingService."""

    def __init__(self, *args, **kwargs):
        pass

    def embed_text(self, text):
        return _vector(0)


class _FakeGeminiGenerationService:
    """Injected in place of ai_assistant.api.ask_api.GeminiGenerationService."""

    last_question = None
    last_context = None
    fixed_answer = "Based on your teachers' feedback, focus on database joins."

    def __init__(self, *args, **kwargs):
        pass

    def generate_answer(self, question, context):
        type(self).last_question = question
        type(self).last_context = context
        return type(self).fixed_answer


class _FailingGeminiGenerationService:
    def __init__(self, *args, **kwargs):
        pass

    def generate_answer(self, question, context):
        raise AnswerGenerationError("Gemini generation request failed: RuntimeError")


@patch("ai_assistant.retrieval.semantic_remarks.GeminiEmbeddingService", _FakeGeminiEmbeddingService)
class AskApiTests(TestCase):

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
            # placement_confirmed=True: authenticate_request() 403s an
            # unconfirmed student before this endpoint's own logic runs.
            return Student.objects.create(
                user=user, parents_phone_number="1234567",
                department=self.department, section=self.section, placement_confirmed=True,
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
        self.enrollment_57 = Enrollment.objects.create(student=self.student_57, course_offering=self.offering_a)

        self.student_80 = make_student("student80@example.com", "Student 80")
        self.enrollment_80 = Enrollment.objects.create(student=self.student_80, course_offering=self.offering_b)

        Attendance.objects.create(enrollment=self.enrollment_57, date=date(2026, 2, 1), status=Attendance.Status.PRESENT)
        Attendance.objects.create(enrollment=self.enrollment_57, date=date(2026, 2, 2), status=Attendance.Status.PRESENT)
        Attendance.objects.create(enrollment=self.enrollment_57, date=date(2026, 2, 3), status=Attendance.Status.ABSENT)

        Attendance.objects.create(enrollment=self.enrollment_80, date=date(2026, 2, 1), status=Attendance.Status.PRESENT)

        self.private_remark = Remark.objects.create(
            student=self.student_57, teacher=self.teacher_a, course_offering=self.offering_a,
            remark_text="Struggling with joins.", visibility=Remark.Visibility.PRIVATE,
        )
        self.visible_remark = Remark.objects.create(
            student=self.student_57, teacher=self.teacher_a, course_offering=self.offering_a,
            remark_text="Improved significantly.", visibility=Remark.Visibility.STUDENT_VISIBLE,
        )
        self.other_teacher_remark = Remark.objects.create(
            student=self.student_80, teacher=self.teacher_b, course_offering=self.offering_b,
            remark_text="Excellent grasp of routing.", visibility=Remark.Visibility.STUDENT_VISIBLE,
        )

        RemarkEmbedding.objects.create(
            remark=self.private_remark, embedding=_vector(60),
        )
        RemarkEmbedding.objects.create(
            remark=self.visible_remark, embedding=_vector(30),
        )
        RemarkEmbedding.objects.create(
            remark=self.other_teacher_remark, embedding=_vector(10),
        )

        now = timezone.now()
        self.pending_assignment = Assignment.objects.create(
            course_offering=self.offering_a, teacher=self.teacher_a,
            title="SQL Homework", description="", due_at=now + timedelta(days=5),
        )
        self.overdue_assignment = Assignment.objects.create(
            course_offering=self.offering_a, teacher=self.teacher_a,
            title="Late Homework", description="", due_at=now - timedelta(days=1),
        )
        self.other_offering_assignment = Assignment.objects.create(
            course_offering=self.offering_b, teacher=self.teacher_b,
            title="Networking Homework", description="", due_at=now + timedelta(days=5),
        )

        self.client = Client()
        _FakeGeminiGenerationService.last_question = None
        _FakeGeminiGenerationService.last_context = None

    def _auth_headers(self, user):
        token = str(RefreshToken.for_user(user).access_token)
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    def _post(self, body, user=None):
        headers = self._auth_headers(user) if user else {}
        return self.client.post(URL, data=json.dumps(body), content_type="application/json", **headers)

    def test_unauthenticated_request_is_rejected(self):
        response = self.client.post(URL, data=json.dumps({"question": "How am I doing?"}), content_type="application/json")
        self.assertEqual(response.status_code, 401)

    @patch("ai_assistant.orchestrator.GeminiGenerationService", _FakeGeminiGenerationService)
    def test_authenticated_student_can_ask_a_question(self):
        response = self._post({"question": "What are my weaknesses?"}, user=self.student_57.user)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["answer"], _FakeGeminiGenerationService.fixed_answer)
        self.assertIn("sources", data)

    @patch("ai_assistant.orchestrator.GeminiGenerationService", _FakeGeminiGenerationService)
    def test_casual_greeting_never_reaches_gemini(self):
        _FakeGeminiGenerationService.last_question = None
        response = self._post({"question": "hello"}, user=self.student_57.user)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["sources"], [])
        self.assertIn("Student", data["answer"])
        self.assertIsNone(_FakeGeminiGenerationService.last_question)

    @patch("ai_assistant.orchestrator.GeminiGenerationService", _FakeGeminiGenerationService)
    def test_casual_thanks_never_reaches_gemini(self):
        _FakeGeminiGenerationService.last_question = None
        response = self._post({"question": "thank you"}, user=self.student_57.user)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["answer"], "You're welcome! Let me know if you need anything else.")
        self.assertIsNone(_FakeGeminiGenerationService.last_question)

    @patch("ai_assistant.orchestrator.GeminiGenerationService", _FailingGeminiGenerationService)
    def test_greeting_plus_attendance_question_still_reaches_gemini(self):
        # "hi, how is my attendance?" is not purely casual - it must still
        # route to the attendance domain and reach Gemini normally. Using
        # the failing fake service here proves this: if the casual layer
        # incorrectly swallowed this question, this would miss the 503.
        response = self._post({"question": "hi, how is my attendance?"}, user=self.student_57.user)
        self.assertEqual(response.status_code, 503)

    @patch("ai_assistant.orchestrator.GeminiGenerationService", _FakeGeminiGenerationService)
    def test_future_course_recommendation_returns_grounded_message_with_no_sources(self):
        _FakeGeminiGenerationService.last_question = None
        response = self._post(
            {"question": "What courses will you recommend me in future?"}, user=self.student_57.user,
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["sources"], [])
        self.assertIsNone(_FakeGeminiGenerationService.last_question)

    @patch("ai_assistant.orchestrator.GeminiGenerationService", _FakeGeminiGenerationService)
    def test_plain_course_question_still_returns_current_courses(self):
        response = self._post({"question": "Which subjects am I having?"}, user=self.student_57.user)

        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(response.json()["sources"]), 0)

    @patch("ai_assistant.orchestrator.GeminiGenerationService", _FakeGeminiGenerationService)
    def test_no_remark_above_similarity_threshold_returns_not_enough_info_without_gemini(self):
        # Every one of student_57's authorized remarks is embedded far
        # (>0.6 cosine distance) from the angle-0 query vector this fake
        # service always returns, so none pass the threshold.
        RemarkEmbedding.objects.filter(remark=self.visible_remark).update(embedding=_vector(170))
        _FakeGeminiGenerationService.last_question = None

        response = self._post({"question": "What are my weaknesses?"}, user=self.student_57.user)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["sources"], [])
        self.assertIn("not enough information", data["answer"].lower())
        self.assertIsNone(_FakeGeminiGenerationService.last_question)

    @patch("ai_assistant.orchestrator.GeminiGenerationService", _FakeGeminiGenerationService)
    def test_student_receives_only_authorized_feedback(self):
        response = self._post({"question": "What are my weaknesses?"}, user=self.student_57.user)
        ids = {s["remark_id"] for s in response.json()["sources"]}
        self.assertEqual(ids, {self.visible_remark.id})

    @patch("ai_assistant.orchestrator.GeminiGenerationService", _FakeGeminiGenerationService)
    def test_private_remarks_never_exposed_to_student(self):
        response = self._post({"question": "What are my weaknesses?"}, user=self.student_57.user)
        ids = {s["remark_id"] for s in response.json()["sources"]}
        self.assertNotIn(self.private_remark.id, ids)

    @patch("ai_assistant.orchestrator.GeminiGenerationService", _FakeGeminiGenerationService)
    def test_another_students_remarks_cannot_appear(self):
        response = self._post({"question": "What are my weaknesses?"}, user=self.student_57.user)
        ids = {s["remark_id"] for s in response.json()["sources"]}
        self.assertNotIn(self.other_teacher_remark.id, ids)

    @patch("ai_assistant.orchestrator.GeminiGenerationService", _FakeGeminiGenerationService)
    def test_student_cannot_override_identity_via_student_id_in_body(self):
        response = self._post(
            {"question": "What are my weaknesses?", "student_id": self.student_80.id}, user=self.student_57.user,
        )
        ids = {s["remark_id"] for s in response.json()["sources"]}
        # student_id in the body is simply never read.
        self.assertEqual(ids, {self.visible_remark.id})
        self.assertNotIn(self.other_teacher_remark.id, ids)

    @patch("ai_assistant.orchestrator.GeminiGenerationService", _FakeGeminiGenerationService)
    def test_teacher_remarks_from_another_teacher_cannot_leak(self):
        response = self._post({"question": "What feedback have I given my students?"}, user=self.teacher_b.user)
        ids = {s["remark_id"] for s in response.json()["sources"]}
        self.assertNotIn(self.private_remark.id, ids)
        self.assertNotIn(self.visible_remark.id, ids)
        self.assertEqual(ids, {self.other_teacher_remark.id})

    @patch("ai_assistant.orchestrator.GeminiGenerationService", _FakeGeminiGenerationService)
    def test_does_not_bypass_phase5_authorization(self):
        from ai_assistant.retrieval.semantic_remarks import get_semantically_relevant_remarks

        direct_results = get_semantically_relevant_remarks(
            self.student_57.user, "What are my weaknesses?", embedding_service=_FakeGeminiEmbeddingService(),
        )
        direct_ids = {r["remark_id"] for r in direct_results}

        response = self._post({"question": "What are my weaknesses?"}, user=self.student_57.user)
        api_ids = {s["remark_id"] for s in response.json()["sources"]}

        self.assertEqual(direct_ids, api_ids)

    @patch("ai_assistant.orchestrator.GeminiGenerationService", _FakeGeminiGenerationService)
    def test_backend_generated_source_ids_match_retrieved_remarks(self):
        response = self._post({"question": "What are my weaknesses?"}, user=self.teacher_a.user)
        sources = response.json()["sources"]
        ids = {s["remark_id"] for s in sources}
        self.assertEqual(ids, {self.private_remark.id, self.visible_remark.id})
        for s in sources:
            self.assertEqual(s["type"], "remark")
            self.assertEqual(set(s.keys()), {"type", "remark_id", "teacher_name", "course_name", "created_at"})

    @patch("ai_assistant.orchestrator.GeminiGenerationService")
    def test_gemini_generated_text_cannot_invent_backend_source_ids(self, mock_service_cls):
        # The response's sources array is built entirely from
        # context["sources"], unaffected by what the answer text says.
        class _InjectingService:
            def __init__(self, *a, **k):
                pass

            def generate_answer(self, question, context):
                return "According to remark #999999, you are doing great."

        mock_service_cls.side_effect = _InjectingService
        response = self._post({"question": "What are my weaknesses?"}, user=self.student_57.user)
        ids = {s["remark_id"] for s in response.json()["sources"]}
        self.assertEqual(ids, {self.visible_remark.id})
        self.assertNotIn(999999, ids)

    def test_empty_retrieval_returns_safe_answer_and_empty_sources(self):
        # Deliberately not mocking GeminiGenerationService here: with zero
        # retrieved remarks, the orchestrator's own "no items from any
        # routed domain" check returns the safe message without constructing
        # GeminiGenerationService at all.
        new_user = User.objects.create_user(email="lonely@example.com", name="Lonely", password="x", role="student")
        lonely_student = Student.objects.create(
            user=new_user, parents_phone_number="1234567",
            department=self.department, section=self.section, placement_confirmed=True,
        )
        response = self._post({"question": "What are my weaknesses?"}, user=lonely_student.user)
        data = response.json()
        self.assertEqual(data["sources"], [])
        self.assertIn("not enough", data["answer"].lower())

    def test_empty_question_is_rejected(self):
        response = self._post({"question": "   "}, user=self.student_57.user)
        self.assertEqual(response.status_code, 400)

    def test_missing_question_is_rejected(self):
        response = self._post({}, user=self.student_57.user)
        self.assertEqual(response.status_code, 400)

    def test_question_too_long_is_rejected(self):
        response = self._post({"question": "x" * 2001}, user=self.student_57.user)
        self.assertEqual(response.status_code, 400)

    def test_invalid_json_body_is_rejected(self):
        response = self.client.post(
            URL, data="not json", content_type="application/json", **self._auth_headers(self.student_57.user),
        )
        self.assertEqual(response.status_code, 400)

    def test_non_object_json_body_is_rejected(self):
        response = self.client.post(
            URL, data=json.dumps(["not", "an", "object"]), content_type="application/json",
            **self._auth_headers(self.student_57.user),
        )
        self.assertEqual(response.status_code, 400)

    def test_get_method_not_allowed(self):
        response = self.client.get(URL, **self._auth_headers(self.student_57.user))
        self.assertEqual(response.status_code, 405)

    @patch("ai_assistant.orchestrator.GeminiGenerationService", _FailingGeminiGenerationService)
    def test_gemini_failure_produces_controlled_error(self):
        response = self._post({"question": "What are my weaknesses?"}, user=self.teacher_a.user)
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("RuntimeError", response.json()["error"])
        self.assertNotIn("Gemini generation request failed", response.json()["error"])

    @patch("ai_assistant.orchestrator.GeminiGenerationService", _FakeGeminiGenerationService)
    def test_api_key_never_exposed_in_success_response(self):
        response = self._post({"question": "What are my weaknesses?"}, user=self.student_57.user)
        self.assertNotIn(settings.GEMINI_API_KEY, response.content.decode())

    @patch("ai_assistant.orchestrator.GeminiGenerationService", _FailingGeminiGenerationService)
    def test_api_key_never_exposed_in_error_response(self):
        response = self._post({"question": "What are my weaknesses?"}, user=self.teacher_a.user)
        self.assertNotIn(settings.GEMINI_API_KEY, response.content.decode())

    @patch("ai_assistant.orchestrator.GeminiGenerationService", _FakeGeminiGenerationService)
    def test_embeddings_and_distance_not_exposed_in_response(self):
        response = self._post({"question": "What are my weaknesses?"}, user=self.teacher_a.user)
        body = response.content.decode()
        self.assertNotIn("embedding", body)
        self.assertNotIn("distance", body)

    @patch("ai_assistant.orchestrator.GeminiGenerationService", _FakeGeminiGenerationService)
    def test_attendance_question_returns_attendance_sources_only(self):
        response = self._post({"question": "How is my attendance?"}, user=self.student_57.user)
        self.assertEqual(response.status_code, 200)
        sources = response.json()["sources"]
        self.assertTrue(sources)
        for s in sources:
            self.assertEqual(s["type"], "attendance")
        self.assertNotIn("remark_id", json.dumps(sources))

    @patch("ai_assistant.orchestrator.GeminiGenerationService", _FakeGeminiGenerationService)
    def test_attendance_question_never_retrieves_remarks(self):
        with patch("ai_assistant.orchestrator.get_semantically_relevant_remarks") as mock_retrieve:
            response = self._post({"question": "How many classes have I missed?"}, user=self.student_57.user)
        self.assertEqual(response.status_code, 200)
        mock_retrieve.assert_not_called()

    @patch("ai_assistant.orchestrator.GeminiGenerationService", _FakeGeminiGenerationService)
    def test_attendance_question_excludes_another_students_attendance(self):
        response = self._post({"question": "How is my attendance?"}, user=self.student_57.user)
        sources = response.json()["sources"]
        course_names = {s["course_name"] for s in sources}
        self.assertEqual(course_names, {"Databases"})

    @patch("ai_assistant.orchestrator.GeminiGenerationService", _FakeGeminiGenerationService)
    def test_combined_question_returns_both_remark_and_attendance_sources(self):
        response = self._post(
            {"question": "How is my attendance and what should I improve?"}, user=self.student_57.user,
        )
        self.assertEqual(response.status_code, 200)
        types = {s["type"] for s in response.json()["sources"]}
        self.assertEqual(types, {"remark", "attendance"})

    def test_unmatched_question_returns_clarification_with_no_retrieval_and_no_gemini_call(self):
        with patch("ai_assistant.orchestrator.get_semantically_relevant_remarks") as mock_retrieve, \
             patch("ai_assistant.orchestrator.build_attendance_context") as mock_attendance, \
             patch("ai_assistant.orchestrator.GeminiGenerationService") as mock_gen:
            response = self._post({"question": "What is the meaning of life?"}, user=self.student_57.user)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["sources"], [])
        mock_retrieve.assert_not_called()
        mock_attendance.assert_not_called()
        mock_gen.assert_not_called()

    @patch("ai_assistant.orchestrator.GeminiGenerationService", _FakeGeminiGenerationService)
    def test_attendance_question_does_not_accept_student_id_override(self):
        response = self._post(
            {"question": "How is my attendance?", "student_id": self.student_80.id}, user=self.student_57.user,
        )
        sources = response.json()["sources"]
        course_names = {s["course_name"] for s in sources}
        self.assertEqual(course_names, {"Databases"})

    @patch("ai_assistant.orchestrator.GeminiGenerationService", _FakeGeminiGenerationService)
    def test_assignment_question_returns_assignment_sources_only(self):
        response = self._post({"question": "What assignments do I have?"}, user=self.student_57.user)
        self.assertEqual(response.status_code, 200)
        sources = response.json()["sources"]
        self.assertTrue(sources)
        for s in sources:
            self.assertEqual(s["type"], "assignment")

    @patch("ai_assistant.orchestrator.GeminiGenerationService", _FakeGeminiGenerationService)
    def test_assignment_question_never_retrieves_remarks_or_attendance(self):
        with patch("ai_assistant.orchestrator.get_semantically_relevant_remarks") as mock_retrieve, \
             patch("ai_assistant.orchestrator.build_attendance_context") as mock_attendance:
            response = self._post({"question": "Do I have any pending assignments?"}, user=self.student_57.user)
        self.assertEqual(response.status_code, 200)
        mock_retrieve.assert_not_called()
        mock_attendance.assert_not_called()

    @patch("ai_assistant.orchestrator.GeminiGenerationService", _FakeGeminiGenerationService)
    def test_assignment_question_excludes_another_students_offering_assignment(self):
        response = self._post({"question": "What assignments do I have?"}, user=self.student_57.user)
        titles = {s["title"] for s in response.json()["sources"]}
        self.assertNotIn("Networking Homework", titles)
        self.assertEqual(titles, {"SQL Homework", "Late Homework"})

    @patch("ai_assistant.orchestrator.GeminiGenerationService", _FakeGeminiGenerationService)
    def test_assignment_overdue_and_pending_statuses_correct_through_api(self):
        response = self._post({"question": "What assignments do I have?"}, user=self.student_57.user)
        by_title = {s["title"]: s for s in response.json()["sources"]}
        self.assertEqual(by_title["Late Homework"]["status"], "overdue")
        self.assertEqual(by_title["SQL Homework"]["status"], "pending")

    @patch("ai_assistant.orchestrator.GeminiGenerationService", _FakeGeminiGenerationService)
    def test_assignment_question_does_not_accept_student_id_override(self):
        response = self._post(
            {"question": "What assignments do I have?", "student_id": self.student_80.id}, user=self.student_57.user,
        )
        titles = {s["title"] for s in response.json()["sources"]}
        self.assertNotIn("Networking Homework", titles)

    @patch("ai_assistant.orchestrator.GeminiGenerationService", _FakeGeminiGenerationService)
    def test_no_attachment_content_or_key_reaches_response(self):
        response = self._post({"question": "What assignments do I have?"}, user=self.student_57.user)
        body = response.content.decode()
        self.assertNotIn("attachment_key", body)
        self.assertNotIn(".pdf", body)

    @patch("ai_assistant.orchestrator.GeminiGenerationService", _FakeGeminiGenerationService)
    def test_combined_attendance_and_assignment_question_returns_both_types(self):
        response = self._post(
            {"question": "How is my attendance and what assignments do I have?"}, user=self.student_57.user,
        )
        types = {s["type"] for s in response.json()["sources"]}
        self.assertEqual(types, {"attendance", "assignment"})

    @patch("ai_assistant.orchestrator.GeminiGenerationService", _FakeGeminiGenerationService)
    def test_course_question_returns_course_sources_only(self):
        response = self._post({"question": "Who teaches me?"}, user=self.student_57.user)
        self.assertEqual(response.status_code, 200)
        sources = response.json()["sources"]
        self.assertTrue(sources)
        for s in sources:
            self.assertEqual(s["type"], "course")

    @patch("ai_assistant.orchestrator.GeminiGenerationService", _FakeGeminiGenerationService)
    def test_course_question_uses_offering_teacher_and_excludes_other_students_course(self):
        response = self._post({"question": "What courses am I taking?"}, user=self.student_57.user)
        sources = response.json()["sources"]
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0]["course_name"], "Databases")
        self.assertEqual(sources[0]["teacher_name"], "Teacher A")
        course_names = {s["course_name"] for s in sources}
        self.assertNotIn("Networks", course_names)

    @patch("ai_assistant.orchestrator.GeminiGenerationService", _FakeGeminiGenerationService)
    def test_course_question_never_retrieves_other_domains(self):
        with patch("ai_assistant.orchestrator.get_semantically_relevant_remarks") as mock_retrieve, \
             patch("ai_assistant.orchestrator.build_attendance_context") as mock_attendance, \
             patch("ai_assistant.orchestrator.build_assignment_context") as mock_assignment:
            response = self._post({"question": "Who teaches me?"}, user=self.student_57.user)
        self.assertEqual(response.status_code, 200)
        mock_retrieve.assert_not_called()
        mock_attendance.assert_not_called()
        mock_assignment.assert_not_called()

    @patch("ai_assistant.orchestrator.GeminiGenerationService", _FakeGeminiGenerationService)
    def test_teacher_feedback_question_does_not_return_course_sources(self):
        response = self._post(
            {"question": "What did my teacher say about my performance?"}, user=self.student_57.user,
        )
        types = {s["type"] for s in response.json()["sources"]}
        self.assertNotIn("course", types)

    @patch("ai_assistant.orchestrator.GeminiGenerationService", _FakeGeminiGenerationService)
    def test_course_question_does_not_accept_student_id_override(self):
        response = self._post(
            {"question": "What courses am I taking?", "student_id": self.student_80.id}, user=self.student_57.user,
        )
        course_names = {s["course_name"] for s in response.json()["sources"]}
        self.assertEqual(course_names, {"Databases"})

    @patch("ai_assistant.orchestrator.GeminiGenerationService", _FakeGeminiGenerationService)
    def test_course_sources_contain_no_internal_ids(self):
        response = self._post({"question": "Who teaches me?"}, user=self.student_57.user)
        for s in response.json()["sources"]:
            self.assertEqual(set(s.keys()), {"type", "course_name", "course_code", "teacher_name", "section_name"})

    @patch("ai_assistant.orchestrator.GeminiGenerationService", _FakeGeminiGenerationService)
    def test_all_four_domains_combined_question(self):
        response = self._post(
            {"question": "Who teaches me, how is my attendance, what assignments do I have, and what should I improve?"},
            user=self.student_57.user,
        )
        types = {s["type"] for s in response.json()["sources"]}
        self.assertEqual(types, {"course", "attendance", "assignment", "remark"})

    @patch("ai_assistant.orchestrator.GeminiGenerationService", _FakeGeminiGenerationService)
    def test_overall_question_activates_all_four_domains_through_api(self):
        response = self._post({"question": "Give me an overall academic summary."}, user=self.student_57.user)
        self.assertEqual(response.status_code, 200)
        types = {s["type"] for s in response.json()["sources"]}
        self.assertEqual(types, {"course", "attendance", "assignment", "remark"})

    def test_unenrolled_course_mention_returns_explicit_not_found_message(self):
        # student_57 is enrolled only in "Databases". No GeminiGenerationService
        # mock needed: this must short-circuit before any Gemini call.
        response = self._post({"question": "How am I doing in Physics?"}, user=self.student_57.user)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["sources"], [])
        self.assertIn("Physics", data["answer"])


@patch("ai_assistant.retrieval.semantic_remarks.GeminiEmbeddingService", _FakeGeminiEmbeddingService)
class CourseScopedNarrowingApiTests(TestCase):
    """
    Proves course-specific narrowing actually excludes an authorized-but-
    different course's data, not just data the student was never authorized
    for. This student is enrolled in two courses to make that testable.
    """

    def setUp(self):
        self.department = Department.objects.create(name="Computing", code="CMP")
        self.section = Section.objects.create(
            name="A", department=self.department, semester_number=1, academic_year=2026,
        )

        teacher_user = User.objects.create_user(email="multi.t@example.com", name="Multi Teacher", password="x", role="teacher")
        self.teacher = Teacher.objects.create(
            user=teacher_user, employee_id="EMP-MULTI", phone_number="1234567",
            department=self.department, designation="Lecturer", qualification="MSc",
            date_of_joining=date(2020, 1, 1), salary=1,
        )

        student_user = User.objects.create_user(email="multi.s@example.com", name="Multi Student", password="x", role="student")
        self.student = Student.objects.create(
            user=student_user, parents_phone_number="1234567",
            department=self.department, section=self.section, placement_confirmed=True,
        )

        self.databases_course = Course.objects.create(
            name="Databases", code="CS201", credits=3, department=self.department, teacher=self.teacher,
        )
        self.databases_offering = CourseOffering.objects.create(
            course=self.databases_course, teacher=self.teacher, semester=CourseOffering.Semester.FALL,
            academic_year=2026, section=self.section,
        )
        self.networks_course = Course.objects.create(
            name="Networks", code="CS202", credits=3, department=self.department, teacher=self.teacher,
        )
        self.networks_offering = CourseOffering.objects.create(
            course=self.networks_course, teacher=self.teacher, semester=CourseOffering.Semester.FALL,
            academic_year=2026, section=self.section,
        )

        self.databases_enrollment = Enrollment.objects.create(
            student=self.student, course_offering=self.databases_offering, status=Enrollment.Status.ACTIVE,
        )
        self.networks_enrollment = Enrollment.objects.create(
            student=self.student, course_offering=self.networks_offering, status=Enrollment.Status.ACTIVE,
        )

        self.databases_remark = Remark.objects.create(
            student=self.student, teacher=self.teacher, course_offering=self.databases_offering,
            remark_text="Strong grasp of SQL joins.", visibility=Remark.Visibility.STUDENT_VISIBLE,
        )
        self.networks_remark = Remark.objects.create(
            student=self.student, teacher=self.teacher, course_offering=self.networks_offering,
            remark_text="Great progress on network protocols.", visibility=Remark.Visibility.STUDENT_VISIBLE,
        )
        RemarkEmbedding.objects.create(
            remark=self.databases_remark, embedding=_vector(30),
        )
        RemarkEmbedding.objects.create(
            remark=self.networks_remark, embedding=_vector(10),
        )

        Attendance.objects.create(
            enrollment=self.databases_enrollment, date=date(2026, 2, 1), status=Attendance.Status.PRESENT,
        )
        Attendance.objects.create(
            enrollment=self.networks_enrollment, date=date(2026, 2, 1), status=Attendance.Status.ABSENT,
        )

        now = timezone.now()
        self.databases_assignment = Assignment.objects.create(
            course_offering=self.databases_offering, teacher=self.teacher,
            title="SQL Homework", description="", due_at=now + timedelta(days=5),
        )
        self.networks_assignment = Assignment.objects.create(
            course_offering=self.networks_offering, teacher=self.teacher,
            title="Routing Homework", description="", due_at=now + timedelta(days=5),
        )

        self.client = Client()

    def _auth_headers(self, user):
        token = str(RefreshToken.for_user(user).access_token)
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    def _post(self, body):
        return self.client.post(
            URL, data=json.dumps(body), content_type="application/json", **self._auth_headers(self.student.user),
        )

    @patch("ai_assistant.orchestrator.GeminiGenerationService", _FakeGeminiGenerationService)
    def test_course_specific_question_excludes_other_authorized_courses_remarks(self):
        response = self._post({"question": "How am I doing in Databases?"})
        self.assertEqual(response.status_code, 200)
        remark_sources = [s for s in response.json()["sources"] if s["type"] == "remark"]
        self.assertTrue(remark_sources)
        for s in remark_sources:
            self.assertEqual(s["course_name"], "Databases")

    @patch("ai_assistant.orchestrator.GeminiGenerationService", _FakeGeminiGenerationService)
    def test_course_specific_question_excludes_other_authorized_courses_attendance(self):
        response = self._post({"question": "How am I doing in Databases?"})
        attendance_sources = [s for s in response.json()["sources"] if s["type"] == "attendance"]
        self.assertTrue(attendance_sources)
        for s in attendance_sources:
            self.assertEqual(s["course_name"], "Databases")

    @patch("ai_assistant.orchestrator.GeminiGenerationService", _FakeGeminiGenerationService)
    def test_course_specific_question_excludes_other_authorized_courses_assignments(self):
        response = self._post({"question": "How am I doing in Databases?"})
        assignment_sources = [s for s in response.json()["sources"] if s["type"] == "assignment"]
        self.assertTrue(assignment_sources)
        titles = {s["title"] for s in assignment_sources}
        self.assertEqual(titles, {"SQL Homework"})
        self.assertNotIn("Routing Homework", titles)

    @patch("ai_assistant.orchestrator.GeminiGenerationService", _FakeGeminiGenerationService)
    def test_course_specific_question_by_code_narrows_identically(self):
        response = self._post({"question": "How am I doing in CS201?"})
        course_sources = [s for s in response.json()["sources"] if s["type"] == "course"]
        self.assertEqual(len(course_sources), 1)
        self.assertEqual(course_sources[0]["course_name"], "Databases")

    @patch("ai_assistant.orchestrator.GeminiGenerationService", _FakeGeminiGenerationService)
    def test_unscoped_question_still_returns_both_courses_data(self):
        # Without course narrowing, both are visible - proves the narrowing
        # test above is actually narrowing.
        response = self._post({"question": "What are my weaknesses?"})
        remark_sources = [s for s in response.json()["sources"] if s["type"] == "remark"]
        course_names = {s["course_name"] for s in remark_sources}
        self.assertEqual(course_names, {"Databases", "Networks"})

    @patch("ai_assistant.orchestrator.GeminiGenerationService", _FakeGeminiGenerationService)
    def test_course_specific_narrowing_does_not_accept_student_id_override(self):
        response = self.client.post(
            URL,
            data=json.dumps({"question": "How am I doing in Databases?", "student_id": 999999}),
            content_type="application/json",
            **self._auth_headers(self.student.user),
        )
        remark_sources = [s for s in response.json()["sources"] if s["type"] == "remark"]
        for s in remark_sources:
            self.assertEqual(s["course_name"], "Databases")
