# Data migration companion to departments/migrations/0003_grant_group_permissions.py -
# same root cause, same fix, for Section instead of Department: section_api
# and section_reference_api are guarded by
# @enforce_permissions('sections', 'section'), but the STUDENT/TEACHER
# groups never had sections.view_section granted, so the Onboarding/Admin
# Section dropdown (dependent on the selected Department) 403'd for every
# real student/teacher session and appeared permanently empty.
#
# View-only: Section is never created/edited/deleted by a student or
# teacher, only read for dropdown selection.
from django.db import migrations


def grant_section_view_permission(apps, schema_editor):
    from django.contrib.auth.management import create_permissions
    from django.apps import apps as global_apps

    app_config = global_apps.get_app_config("sections")
    app_config.models_module = app_config.models_module or True
    create_permissions(app_config, verbosity = 0)

    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")

    section_content_type = ContentType.objects.get(app_label = "sections", model = "section")
    view_perm = Permission.objects.get(content_type = section_content_type, codename = "view_section")

    for group_name in ("STUDENT", "TEACHER"):
        group, _ = Group.objects.get_or_create(name = group_name)
        group.permissions.add(view_perm)


def revoke_section_view_permission(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")

    section_content_type = ContentType.objects.filter(app_label = "sections", model = "section").first()
    if not section_content_type:
        return

    view_perm = Permission.objects.filter(content_type = section_content_type, codename = "view_section")

    for group_name in ("STUDENT", "TEACHER"):
        group = Group.objects.filter(name = group_name).first()
        if group:
            group.permissions.remove(*view_perm)


class Migration(migrations.Migration):

    dependencies = [
        ("sections", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(grant_section_view_permission, revoke_section_view_permission),
    ]
