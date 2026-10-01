from django.db import models
from teachers.models import Teacher
from students.models import Student
from course_offerings.models import CourseOffering

class Assignment(models.Model):
    course_offering = models.ForeignKey(CourseOffering, on_delete = models.PROTECT, related_name = "assignments")
    teacher = models.ForeignKey(Teacher, on_delete = models.PROTECT, related_name = "assignments")
    title = models.CharField(max_length = 255)
    description = models.TextField(blank = True)
    due_at = models.DateTimeField()
    # Set via the two-step upload flow (attachment-upload-url/ then
    # attachment-confirm/), same pattern as Student/Teacher profile pictures.
    attachment_key = models.CharField(max_length = 255, null = True, blank = True)
    created_at = models.DateTimeField(auto_now_add = True)
    updated_at = models.DateTimeField(auto_now = True)

    def __str__(self): return f"{self.title} - {self.course_offering}"


class Submission(models.Model):
    # CASCADE: a submission has no meaning once its assignment is gone.
    assignment = models.ForeignKey(Assignment, on_delete = models.CASCADE, related_name = "submissions")
    student = models.ForeignKey(Student, on_delete = models.CASCADE, related_name = "submissions")
    file_key = models.CharField(max_length = 255)
    # auto_now: resubmitting overwrites this same row (see unique_together),
    # so "submitted_at" always reflects the latest upload with no extra logic.
    submitted_at = models.DateTimeField(auto_now = True)

    class Meta:
        constraints = [
            # One submission per student per assignment - resubmitting before
            # the due date replaces this row rather than creating a new one.
            models.UniqueConstraint(fields = ["assignment", "student"], name = "unique_assignment_student_submission"),
        ]

    def __str__(self): return f"{self.student} - {self.assignment}"


class AssignmentEvaluation(models.Model):
    """
    Phase 11B: AI Assignment Evaluation. Holds two distinct things, kept
    deliberately separate for auditability:

    AI-generated (never trusted as final):
        suggested_score, strengths, weaknesses, ai_feedback, confidence

    Teacher-controlled (the only thing that is ever authoritative):
        final_score, teacher_feedback, status

    AI suggestion != final grade. final_score/teacher_feedback stay null/
    blank until a teacher explicitly reviews and saves a decision - nothing
    in this model or the services around it ever sets them automatically.

    OneToOneField to Submission (same reasoning as RemarkEmbedding's
    OneToOneField to Remark in Phase 3): one evaluation per submission,
    automatic cascade-delete safety, and re-running "AI Check" updates this
    same row rather than creating duplicates.
    """
    class Status(models.TextChoices):
        AI_SUGGESTED = "AI_SUGGESTED", "AI Suggested"
        APPROVED = "APPROVED", "Approved"
        EDITED = "EDITED", "Edited"
        REJECTED = "REJECTED", "Rejected"

    submission = models.OneToOneField(Submission, on_delete=models.CASCADE, related_name="evaluation")

    # AI-generated - a suggestion only.
    suggested_score = models.PositiveIntegerField(null=True, blank=True)
    strengths = models.JSONField(default=list, blank=True)
    weaknesses = models.JSONField(default=list, blank=True)
    ai_feedback = models.TextField(blank=True)
    confidence = models.CharField(max_length=10, blank=True)

    # Teacher-controlled - the only authoritative fields. Null/blank until
    # a teacher actually reviews and saves a decision.
    final_score = models.PositiveIntegerField(null=True, blank=True)
    teacher_feedback = models.TextField(blank=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AI_SUGGESTED)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self): return f"Evaluation for {self.submission} ({self.status})"
