from django.db import models

# Create your models here.from django.db import models

class Student(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)

    student_email = models.EmailField(unique=True)

    parents_phone_number = models.CharField(max_length=20)

    date_of_birth = models.DateField()

    gender = models.CharField(max_length=1, blank=True, null=True)

    address = models.TextField(blank=True, null=True)

    student_group = models.CharField(max_length=100)

    date_of_enrollment = models.DateField(auto_now_add=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
