# Data migration granting the TEACHER group the Attendance model permissions
# @enforce_permissions('attendance', 'attendance') requires - same fix/pattern
# as assignments/migrations/0002_grant_group_permissions.py and
# remarks/migrations/0002_grant_group_permissions.py.
#
# Without this, every teacher account gets a 403 on POST/PUT/PATCH/DELETE
# /attendance/ (and /attendance/bulk/) regardless of whose class it is - this
# grant was never created for the attendance app (unlike assignments/remarks).
#
# This ONLY grants the Django permission that lets a teacher's request reach
# the view at all. It does not touch, weaken, or replace the actual ownership
# check - attendance_service.create()/update()/create_bulk() still separately
# enforce `enrollment.course_offering.teacher_id == teacher.id` for every
# write, so a teacher with this permission can still only write attendance
# for their OWN course offerings. Final authorization is the AND of both:
# Django permission (this migration) + ownership check (unchanged service code).
#
# ADMIN is deliberately NOT touched here - out of scope for this fix.
from django.db import migrations


def grant_teacher_attendance_permissions(apps, schema_editor):
    from django.contrib.auth.management import create_permissions
    from django.apps import apps as global_apps

    app_config = global_apps.get_app_config("attendance")
    app_config.models_module = app_config.models_module or True
    create_permissions(app_config, verbosity = 0)

    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")

    attendance_ct = ContentType.objects.get(app_label = "attendance", model = "attendance")

    attendance_view = Permission.objects.get(content_type = attendance_ct, codename = "view_attendance")
    attendance_add = Permission.objects.get(content_type = attendance_ct, codename = "add_attendance")
    attendance_change = Permission.objects.get(content_type = attendance_ct, codename = "change_attendance")
    attendance_delete = Permission.objects.get(content_type = attendance_ct, codename = "delete_attendance")

    teacher_group, _ = Group.objects.get_or_create(name = "TEACHER")
    teacher_group.permissions.add(attendance_view, attendance_add, attendance_change, attendance_delete)


def revoke_teacher_attendance_permissions(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")

    content_types = ContentType.objects.filter(app_label = "attendance", model = "attendance")
    perms = Permission.objects.filter(content_type__in = content_types)

    teacher_group = Group.objects.filter(name = "TEACHER").first()
    if teacher_group:
        teacher_group.permissions.remove(*perms)


class Migration(migrations.Migration):

    dependencies = [
        ("attendance", "0002_attendance_is_deleted"),
    ]

    operations = [
        migrations.RunPython(grant_teacher_attendance_permissions, revoke_teacher_attendance_permissions),
    ]
