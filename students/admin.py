from django.contrib import admin
from .models import Student


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    # The `user` FK is the authentication-identity link (which User account
    # this Student profile belongs to) - it must never be hand-picked from a
    # dropdown here, since a mismatch here is a mismatch between what a
    # person logs in as and whose data they see everywhere in the app.
    readonly_fields = ("user",)
