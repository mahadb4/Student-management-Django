# Data migration that fixes the Student/Teacher Onboarding Department
# dropdown being permanently empty (looked "greyed out"/disabled in the UI,
# because nothing ever loaded into it): department_api and
# department_reference_api are both guarded by
# @enforce_permissions('departments', 'department'), but nothing anywhere in
# the project ever attached the actual departments.view_department
# Permission to the STUDENT or TEACHER group - user_repository.py only ever
# creates the Group itself, never seeds its permissions. So every non-admin
# GET /departments/reference/ (used by Student/Teacher Onboarding and the
# Admin Edit Student form) 403'd for every real student/teacher session.
# Same root cause/pattern already fixed once for remarks
# (remarks/migrations/0002_grant_group_permissions.py) and once for
# attendance (attendance/migrations/0003_grant_teacher_group_permissions.py).
#
# View-only: Department is never created/edited/deleted by a student or
# teacher, only read for dropdown selection.
from django.db import migrations


def grant_department_view_permission(apps, schema_editor):
    from django.contrib.auth.management import create_permissions
    from django.apps import apps as global_apps

    app_config = global_apps.get_app_config("departments")
    app_config.models_module = app_config.models_module or True
    create_permissions(app_config, verbosity = 0)

    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")

    department_content_type = ContentType.objects.get(app_label = "departments", model = "department")
    view_perm = Permission.objects.get(content_type = department_content_type, codename = "view_department")

    for group_name in ("STUDENT", "TEACHER"):
        group, _ = Group.objects.get_or_create(name = group_name)
        group.permissions.add(view_perm)


def revoke_department_view_permission(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")

    department_content_type = ContentType.objects.filter(app_label = "departments", model = "department").first()
    if not department_content_type:
        return

    view_perm = Permission.objects.filter(content_type = department_content_type, codename = "view_department")

    for group_name in ("STUDENT", "TEACHER"):
        group = Group.objects.filter(name = group_name).first()
        if group:
            group.permissions.remove(*view_perm)


class Migration(migrations.Migration):

    dependencies = [
        ("departments", "0002_department_is_deleted"),
    ]

    operations = [
        migrations.RunPython(grant_department_view_permission, revoke_department_view_permission),
    ]
