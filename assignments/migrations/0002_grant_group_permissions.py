# Data migration granting the TEACHER/STUDENT groups the model permissions
# their assignment_api/submission_api views require via @enforce_permissions
# - same fix, and same reasoning, as remarks/migrations/0002_grant_group_permissions.py.
#
# TEACHER: full CRUD on Assignment (create/edit/delete their own classes'
# assignments), view-only on Submission (they only ever read submissions,
# never create/edit/delete one themselves).
# STUDENT: view-only on Assignment (they only read assignments for their
# enrolled classes), add/view/change on Submission (create + resubmit before
# the due date; no delete - a submission is replaced, never removed).
from django.db import migrations


def grant_assignments_permissions(apps, schema_editor):
    from django.contrib.auth.management import create_permissions
    from django.apps import apps as global_apps

    app_config = global_apps.get_app_config("assignments")
    app_config.models_module = app_config.models_module or True
    create_permissions(app_config, verbosity = 0)

    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")

    assignment_ct = ContentType.objects.get(app_label = "assignments", model = "assignment")
    submission_ct = ContentType.objects.get(app_label = "assignments", model = "submission")

    assignment_view = Permission.objects.get(content_type = assignment_ct, codename = "view_assignment")
    assignment_add = Permission.objects.get(content_type = assignment_ct, codename = "add_assignment")
    assignment_change = Permission.objects.get(content_type = assignment_ct, codename = "change_assignment")
    assignment_delete = Permission.objects.get(content_type = assignment_ct, codename = "delete_assignment")

    submission_view = Permission.objects.get(content_type = submission_ct, codename = "view_submission")
    submission_add = Permission.objects.get(content_type = submission_ct, codename = "add_submission")
    submission_change = Permission.objects.get(content_type = submission_ct, codename = "change_submission")

    teacher_group, _ = Group.objects.get_or_create(name = "TEACHER")
    teacher_group.permissions.add(assignment_view, assignment_add, assignment_change, assignment_delete, submission_view)

    student_group, _ = Group.objects.get_or_create(name = "STUDENT")
    student_group.permissions.add(assignment_view, submission_view, submission_add, submission_change)


def revoke_assignments_permissions(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")

    content_types = ContentType.objects.filter(app_label = "assignments", model__in = ["assignment", "submission"])
    perms = Permission.objects.filter(content_type__in = content_types)

    for group_name in ("TEACHER", "STUDENT"):
        group = Group.objects.filter(name = group_name).first()
        if group:
            group.permissions.remove(*perms)


class Migration(migrations.Migration):

    dependencies = [
        ("assignments", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(grant_assignments_permissions, revoke_assignments_permissions),
    ]
