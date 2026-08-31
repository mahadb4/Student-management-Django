# Generated manually

from django.db import migrations

def link_teachers_to_users(apps, schema_editor):
    Teacher = apps.get_model('teachers', 'Teacher')
    User = apps.get_model('users', 'User')
    
    for teacher in Teacher.objects.all():
        user = User.objects.filter(email = teacher.email).first()
        if user:
            teacher.user = user
            teacher.save(update_fields = ['user'])

class Migration(migrations.Migration):

    dependencies = [
        ('teachers', '0002_teacher_user'),
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(link_teachers_to_users),
    ]
