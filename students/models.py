from django.db import models
from departments.models import Department
from teachers.models import Teacher

class Student(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    student_email = models.EmailField(unique=True)
    parents_phone_number = models.CharField(max_length=20)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=1, choices=[("M", "Male"), ("F", "Female")])
    address = models.TextField(blank=True, null=True)
    student_group = models.CharField(max_length=100)
    department = models.ForeignKey(
        "departments.Department",
        on_delete=models.PROTECT,
        related_name="students",
        null=True,
        blank=True,
    )
    teacher = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True, blank=True, related_name="students")
    date_of_enrollment = models.DateField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"