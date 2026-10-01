from django.db import models
from students.models import Student
from teachers.models import Teacher
from course_offerings.models import CourseOffering

class Remark(models.Model):
    class Visibility(models.IntegerChoices):
        PRIVATE = 0,"Private"
        STUDENT_VISIBLE = 1,"Student Visible"

    student = models.ForeignKey(Student,on_delete = models.CASCADE,related_name = "remarks")
    teacher = models.ForeignKey(Teacher,on_delete = models.PROTECT,related_name = "remarks")
    course_offering = models.ForeignKey(CourseOffering,on_delete = models.PROTECT,related_name = "remarks")
    remark_text = models.TextField()
    visibility = models.PositiveSmallIntegerField(choices = Visibility.choices,default = Visibility.PRIVATE)
    created_at = models.DateTimeField(auto_now_add = True)
    updated_at = models.DateTimeField(auto_now = True)

    def __str__(self): return f"{self.student} - {self.course_offering} - {self.created_at:%Y-%m-%d}"


# The external API/RAG contract keeps speaking the original string labels;
# only the DB column is now an int. This is the single translation point.
VISIBILITY_CODE_TO_LABEL = {
    Remark.Visibility.PRIVATE: "PRIVATE",
    Remark.Visibility.STUDENT_VISIBLE: "STUDENT_VISIBLE",
}
VISIBILITY_LABEL_TO_CODE = {label: code for code, label in VISIBILITY_CODE_TO_LABEL.items()}
