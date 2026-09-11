# Data migration that fixes the "Permission denied: remarks.view_remark
# required." error teachers/students were getting on /api/remarks/.
#
# Root cause: users/repositories/user_repository.py adds every approved user
# to a Group named after their role (TEACHER/STUDENT/...), and remark_api is
# guarded by @enforce_permissions('remarks', 'remark') which checks Django's
# real has_perm(). But nothing anywhere in the project ever attached the
# actual Permission rows (view_remark/add_remark/...) to those groups, so
# has_perm() was always False for non-superusers. This migration grants the
# TEACHER group full CRUD on remarks (they create/edit/delete their own) and
# the STUDENT group view-only (they only ever read their own remarks) -
# matching the existing project convention of Django's built-in Group/
# Permission system, not a custom mechanism.
from django.db import migrations


def grant_remarks_permissions(apps, schema_editor):
    # Model permissions (view_remark, add_remark, ...) are normally created by
    # Django's post_migrate signal AFTER every app has migrated, so on a brand
    # new database they may not exist yet at this point in the migration run.
    # Creating them explicitly here makes this migration safe regardless of
    # ordering.
    from django.contrib.auth.management import create_permissions
    from django.apps import apps as global_apps

    app_config = global_apps.get_app_config("remarks")
    app_config.models_module = app_config.models_module or True
    create_permissions(app_config, verbosity = 0)

    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")

    remark_content_type = ContentType.objects.get(app_label = "remarks", model = "remark")
    view_perm = Permission.objects.get(content_type = remark_content_type, codename = "view_remark")
    add_perm = Permission.objects.get(content_type = remark_content_type, codename = "add_remark")
    change_perm = Permission.objects.get(content_type = remark_content_type, codename = "change_remark")
    delete_perm = Permission.objects.get(content_type = remark_content_type, codename = "delete_remark")

    teacher_group, _ = Group.objects.get_or_create(name = "TEACHER")
    teacher_group.permissions.add(view_perm, add_perm, change_perm, delete_perm)

    student_group, _ = Group.objects.get_or_create(name = "STUDENT")
    student_group.permissions.add(view_perm)


def revoke_remarks_permissions(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")

    remark_content_type = ContentType.objects.filter(app_label = "remarks", model = "remark").first()
    if not remark_content_type:
        return

    remark_perms = Permission.objects.filter(content_type = remark_content_type)

    for group_name in ("TEACHER", "STUDENT"):
        group = Group.objects.filter(name = group_name).first()
        if group:
            group.permissions.remove(*remark_perms)


class Migration(migrations.Migration):

    dependencies = [
        ("remarks", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(grant_remarks_permissions, revoke_remarks_permissions),
    ]
