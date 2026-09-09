from django.db import models
from common.utils import split_display_name
from departments.models import Department
from sections.models import Section

class Student(models.Model):
    # Identity (name/email) lives on User. Every Student has one.
    user = models.OneToOneField(
        "users.User",
        on_delete = models.CASCADE,
        related_name = "student_profile")

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

    def __str__(self): return self.user.name

    @property
    def effective_first_name(self):
        return split_display_name(self.user.name)[0]

    @property
    def effective_last_name(self):
        return split_display_name(self.user.name)[1]

    @property
    def effective_email(self):
        return self.user.email