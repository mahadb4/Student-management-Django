# Generated manually

from django.db import migrations

def link_students_to_users(apps, schema_editor):
    Student = apps.get_model('students', 'Student')
    User = apps.get_model('users', 'User')
    
    for student in Student.objects.all():
        user = User.objects.filter(email = student.student_email).first()
        if user:
            student.user = user
            student.save(update_fields = ['user'])

class Migration(migrations.Migration):

    dependencies = [
        ('students', '0002_student_user'),
        ('users', '0001_initial'),  # ensure users app is loaded
    ]

    operations = [
        migrations.RunPython(link_students_to_users),
    ]
