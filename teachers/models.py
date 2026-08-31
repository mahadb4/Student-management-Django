from django.db import models
from django.utils import timezone
from departments.models import Department

class Teacher(models.Model):
    user = models.OneToOneField("users.User",on_delete = models.CASCADE,null = True,blank = True,related_name = "teacher_profile")
    first_name = models.CharField(max_length = 100)
    last_name = models.CharField(max_length = 100)
    employee_id = models.CharField(max_length = 20,unique = True)
    email = models.EmailField(unique = True)
    phone_number = models.CharField(max_length = 20)
    department = models.ForeignKey(Department,on_delete = models.PROTECT,related_name = "teachers")
    designation = models.CharField(max_length = 100)
    qualification = models.CharField(max_length = 100)
    gender = models.CharField(max_length = 1,choices = [("M","Male"),("F","Female")])
    date_of_birth = models.DateField()
    date_of_joining = models.DateField(default = timezone.now)
    salary = models.DecimalField(max_digits = 10,decimal_places = 2)
    address = models.TextField(blank = True,null = True)
    is_active = models.BooleanField(default = True)
    is_deleted = models.BooleanField(default = False)
    created_at = models.DateTimeField(auto_now_add = True)
    updated_at = models.DateTimeField(auto_now = True)

    def __str__(self): return f"{self.first_name} {self.last_name}"