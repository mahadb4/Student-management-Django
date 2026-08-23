from django.db import models

class Department(models.Model):
    name = models.CharField(max_length=100,unique=True)
    code = models.CharField(max_length=20,unique=True)
    description = models.TextField(blank=True,null=True)
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self): return self.name