from students.models import Student
from teachers.models import Teacher

def apply_data_scope(user, queryset, model_type):
    if not user.is_authenticated:
        return queryset.none()
    if user.is_superuser:
        return queryset

    try:
        user_student = user.student_profile
    except Exception as e:
        print("EXCEPTION:", repr(e))
        user_student = None

    try:
        user_teacher = user.teacher_profile
    except Exception as e:
        print("EXCEPTION:", repr(e))
        user_teacher = None

    if model_type == 'student':
        if user_teacher:
            return queryset.filter(enrollments__course_offering__teacher=user_teacher).distinct()
        if user_student:
            return queryset.filter(id=user_student.id)
        return queryset.none()
    
    if model_type == 'teacher':
        if user_teacher:
            return queryset.filter(id=user_teacher.id)
        if user_student:
            return queryset.filter(courseoffering__enrollment__student=user_student).distinct()
        return queryset.none()

    if model_type in ['course_offering', 'courseoffering']:
        if user_teacher:
            return queryset.filter(teacher=user_teacher)
        if user_student:
            return queryset.filter(enrollment__student=user_student)
        return queryset.none()

    if model_type == 'enrollment':
        if user_teacher:
            return queryset.filter(course_offering__teacher=user_teacher)
        if user_student:
            return queryset.filter(student=user_student)
        return queryset.none()

    if model_type == 'attendance':
        if user_teacher:
            return queryset.filter(enrollment__course_offering__teacher=user_teacher)
        if user_student:
            return queryset.filter(enrollment__student=user_student)
        return queryset.none()

    if model_type in ['course', 'department']:
        return queryset

    return queryset.none()
