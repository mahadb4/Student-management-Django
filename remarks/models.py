from django.db import models
from students.models import Student
from teachers.models import Teacher
from course_offerings.models import CourseOffering

class Remark(models.Model):
    class Visibility(models.TextChoices):
        PRIVATE = "PRIVATE","Private"
        STUDENT_VISIBLE = "STUDENT_VISIBLE","Student Visible"

    student = models.ForeignKey(Student,on_delete = models.CASCADE,related_name = "remarks")
    teacher = models.ForeignKey(Teacher,on_delete = models.PROTECT,related_name = "remarks")
    course_offering = models.ForeignKey(CourseOffering,on_delete = models.PROTECT,related_name = "remarks")
    remark_text = models.TextField()
    visibility = models.CharField(max_length = 20,choices = Visibility.choices,default = Visibility.PRIVATE)
    created_at = models.DateTimeField(auto_now_add = True)
    updated_at = models.DateTimeField(auto_now = True)

    def __str__(self): return f"{self.student} - {self.course_offering} - {self.created_at:%Y-%m-%d}"
