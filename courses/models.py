from django.db import models
from departments.models import Department
from teachers.models import Teacher

class Course(models.Model):
    name = models.CharField(max_length = 150)
    code = models.CharField(max_length = 20, unique = True)
    description = models.TextField(blank = True, null = True)
    credits = models.PositiveIntegerField()
    department = models.ForeignKey(Department, on_delete = models.PROTECT, related_name = "courses")
    teacher = models.ForeignKey(Teacher, on_delete = models.SET_NULL, null = True, blank = True, related_name = "courses")
    # Which program semester (1-8) this course's curriculum belongs to. Distinct
    # from CourseOffering.semester (Fall/Spring/Summer academic term) and from
    # Section.semester_number (the section's own program semester) - this is the
    # semester the COURSE is designed for. Nullable: existing courses predate
    # this field and aren't part of a classified curriculum yet.
    semester_number = models.PositiveIntegerField(null = True, blank = True)
    is_active = models.BooleanField(default = True)
    created_at = models.DateTimeField(auto_now_add = True)
    updated_at = models.DateTimeField(auto_now = True)

    def __str__(self):
        return f"{self.code} - {self.name}"