from django.db import models
from departments.models import Department
from sections.models import Section

class Student(models.Model):
    user = models.OneToOneField(
        "users.User",
        on_delete = models.CASCADE,
        null = True, blank = True,
        related_name = "student_profile")
    
    first_name = models.CharField(max_length = 100)
    last_name = models.CharField(max_length = 100)
    student_email = models.EmailField(unique = True)
    parents_phone_number = models.CharField(max_length = 20)
    date_of_birth = models.DateField()

    gender = models.CharField(
        max_length = 1,
        choices = [("M","Male"),("F","Female")])
    
    address = models.TextField(blank = True,null = True)

    department = models.ForeignKey(
        Department,on_delete = models.PROTECT,
        related_name = "students",null = True,blank = True)
    
    section = models.ForeignKey(
        Section,on_delete = models.PROTECT,
        related_name = "students",null = True,blank = True)
    
    date_of_enrollment = models.DateField(auto_now_add = True)
    is_active = models.BooleanField(default = True)
    is_deleted = models.BooleanField(default = False)
    created_at = models.DateTimeField(auto_now_add = True)
    updated_at = models.DateTimeField(auto_now = True)

    def __str__(self): return f"{self.first_name} {self.last_name}"