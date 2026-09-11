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
