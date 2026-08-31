from django.db import models
from courses.models import Course
from teachers.models import Teacher
from sections.models import Section

class CourseOffering(models.Model):
    class Semester(models.TextChoices):
        SPRING = "SPRING","Spring"
        SUMMER = "SUMMER","Summer"
        FALL = "FALL","Fall"

    course = models.ForeignKey(Course,on_delete = models.PROTECT,related_name = "offerings")
    teacher = models.ForeignKey(Teacher,on_delete = models.PROTECT,related_name = "course_offerings")
    semester = models.CharField(max_length = 10,choices = Semester.choices)
    academic_year = models.PositiveIntegerField()
    section = models.ForeignKey(Section,on_delete = models.PROTECT,related_name = "course_offerings",null = True,blank = True)
    is_active = models.BooleanField(default = True)
    is_deleted = models.BooleanField(default = False)
    created_at = models.DateTimeField(auto_now_add = True)
    updated_at = models.DateTimeField(auto_now = True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields = ["course","teacher","semester","academic_year","section"],
                name = "unique_course_offering"
            )
        ]

    def __str__(self):
        section_name = self.section.name if self.section else "No Section"
        return f"{self.course.code} - {section_name} - {self.get_semester_display()} {self.academic_year}"