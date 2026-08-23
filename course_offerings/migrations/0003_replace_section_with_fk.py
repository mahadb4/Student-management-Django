from django.db import migrations,models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ("sections","0001_initial"),
        ("course_offerings","0002_courseoffering_is_deleted"),
    ]

    operations = [
        migrations.RenameField(
            model_name="courseoffering",
            old_name="section",
            new_name="old_section",
        ),
        migrations.AddField(
            model_name="courseoffering",
            name="section",
            field=models.ForeignKey(
                to="sections.section",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="course_offerings",
                null=True,
                blank=True,
            ),
        ),
        migrations.RemoveField(
            model_name="courseoffering",
            name="old_section",
        ),
    ]