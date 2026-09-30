from django.db import migrations, models


def convert_visibility_strings_to_codes(apps, schema_editor):
    Remark = apps.get_model("remarks", "Remark")
    Remark.objects.filter(visibility="PRIVATE").update(visibility_code=0)
    Remark.objects.filter(visibility="STUDENT_VISIBLE").update(visibility_code=1)


def convert_visibility_codes_to_strings(apps, schema_editor):
    Remark = apps.get_model("remarks", "Remark")
    Remark.objects.filter(visibility_code=0).update(visibility="PRIVATE")
    Remark.objects.filter(visibility_code=1).update(visibility="STUDENT_VISIBLE")


class Migration(migrations.Migration):

    dependencies = [
        ("remarks", "0002_grant_group_permissions"),
    ]

    operations = [
        migrations.AddField(
            model_name="remark",
            name="visibility_code",
            field=models.PositiveSmallIntegerField(null=True),
        ),
        migrations.RunPython(convert_visibility_strings_to_codes, convert_visibility_codes_to_strings),
        migrations.RemoveField(
            model_name="remark",
            name="visibility",
        ),
        migrations.RenameField(
            model_name="remark",
            old_name="visibility_code",
            new_name="visibility",
        ),
        migrations.AlterField(
            model_name="remark",
            name="visibility",
            field=models.PositiveSmallIntegerField(
                choices=[(0, "Private"), (1, "Student Visible")], default=0,
            ),
        ),
    ]
