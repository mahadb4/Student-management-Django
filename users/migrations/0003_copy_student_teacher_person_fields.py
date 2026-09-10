from django.db import migrations


def copy_forward(apps, schema_editor):
    Student = apps.get_model("students", "Student")
    Teacher = apps.get_model("teachers", "Teacher")

    for student in Student.objects.select_related("user").all():
        user = student.user
        user.date_of_birth = student.date_of_birth
        user.gender = student.gender
        user.address = student.address
        user.profile_picture_key = student.profile_picture_key
        user.save(update_fields = ["date_of_birth", "gender", "address", "profile_picture_key"])

    for teacher in Teacher.objects.select_related("user").all():
        user = teacher.user
        user.date_of_birth = teacher.date_of_birth
        user.gender = teacher.gender
        user.address = teacher.address
        user.profile_picture_key = teacher.profile_picture_key
        user.save(update_fields = ["date_of_birth", "gender", "address", "profile_picture_key"])


def copy_backward(apps, schema_editor):
    # No-op: the source columns on Student/Teacher are untouched by this
    # migration (they are only removed by a later, separate migration), so
    # there is nothing to restore here.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0002_user_address_user_date_of_birth_user_gender_and_more"),
        ("students", "0006_student_profile_picture_key"),
        ("teachers", "0007_teacher_profile_picture_key"),
    ]

    operations = [
        migrations.RunPython(copy_forward, copy_backward),
    ]
