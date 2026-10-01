from django.db import models
from django.utils import timezone
from common.utils import split_display_name
from departments.models import Department

class Teacher(models.Model):
    # Identity (name/email) lives on User. Every Teacher has one.
    user = models.OneToOneField("users.User",on_delete = models.CASCADE,related_name = "teacher_profile")
    employee_id = models.CharField(max_length = 20,unique = True)
    phone_number = models.CharField(max_length = 20)
    department = models.ForeignKey(Department,on_delete = models.PROTECT,related_name = "teachers")
    designation = models.CharField(max_length = 100)
    qualification = models.CharField(max_length = 100)
    date_of_joining = models.DateField(default = timezone.now)
    salary = models.DecimalField(max_digits = 10,decimal_places = 2)

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