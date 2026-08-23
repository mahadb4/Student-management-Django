from django.db import models
from departments.models import Department

class Section(models.Model):
    name = models.CharField(max_length=50)
    department = models.ForeignKey(Department,on_delete=models.PROTECT,related_name="sections")
    semester_number = models.PositiveIntegerField()
    academic_year = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["name","department","semester_number","academic_year"],name="unique_section"),
        ]

    def __str__(self): return f"{self.department} - Semester {self.semester_number} - {self.name}"