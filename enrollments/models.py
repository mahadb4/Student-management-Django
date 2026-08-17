from django.db import models
from students.models import Student
from course_offerings.models import CourseOffering

class Enrollment(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        DROPPED = "DROPPED", "Dropped"
        COMPLETED = "COMPLETED", "Completed"

    student = models.ForeignKey(Student, on_delete=models.PROTECT, related_name="enrollments")
    course_offering = models.ForeignKey(CourseOffering, on_delete=models.PROTECT, related_name="enrollments")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    enrolled_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["student", "course_offering"],
                name="unique_student_course_offering",
            ),
        ]

    def __str__(self):
        return f"{self.student} - {self.course_offering}"