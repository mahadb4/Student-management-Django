from datetime import date
from django.db import transaction
from departments.models import Department
from teachers.models import Teacher
from students.models import Student
from courses.models import Course
from course_offerings.models import CourseOffering
from enrollments.models import Enrollment
from attendance.models import Attendance

@transaction.atomic
def seed_data():
    print("\nCreating departments...")

    department_data = [
        ("Computer Science", "CS"),
        ("Software Engineering", "SE"),
        ("Artificial Intelligence", "AI"),
        ("Data Science", "DS"),
        ("Information Technology", "IT"),
        ("Electrical Engineering", "EE"),
        ("Business Administration", "BBA"),
        ("Accounting and Finance", "AF"),
        ("Media Sciences", "MS"),
        ("Mathematics", "MATH"),
    ]

    departments = []

    for name, code in department_data:
        department, _ = Department.objects.get_or_create(
            code = code,
            defaults = {
                "name": name,
                "description": f"{name} Department",
                "is_active": True,
            },
        )

        departments.append(department)

    print(f"Departments ready: {len(departments)}")

    print("\nCreating teachers...")

    teacher_data = [
        ("Ahmed", "Khan", "T001", "ahmed.khan@university.edu", "M"),
        ("Sara", "Ahmed", "T002", "sara.ahmed@university.edu", "F"),
        ("Usman", "Ali", "T003", "usman.ali@university.edu", "M"),
        ("Ayesha", "Malik", "T004", "ayesha.malik@university.edu", "F"),
        ("Hamza", "Raza", "T005", "hamza.raza@university.edu", "M"),
        ("Fatima", "Sheikh", "T006", "fatima.sheikh@university.edu", "F"),
        ("Bilal", "Hassan", "T007", "bilal.hassan@university.edu", "M"),
        ("Hina", "Aslam", "T008", "hina.aslam@university.edu", "F"),
        ("Omar", "Farooq", "T009", "omar.farooq@university.edu", "M"),
        ("Zainab", "Iqbal", "T010", "zainab.iqbal@university.edu", "F"),
    ]

    teachers = []

    teacher_designations = [
        "Professor",
        "Associate Professor",
        "Assistant Professor",
        "Assistant Professor",
        "Lecturer",
        "Lecturer",
        "Assistant Professor",
        "Lecturer",
        "Assistant Professor",
        "Lecturer",
    ]

    teacher_qualifications = [
        "PhD Computer Science",
        "MS Software Engineering",
        "MS Artificial Intelligence",
        "MS Data Science",
        "MS Computer Science",
        "MS Information Technology",
        "MS Electrical Engineering",
        "MBA",
        "MS Finance",
        "MS Mathematics",
    ]

    for index, (
        first_name,
        last_name,
        employee_id,
        email,
        gender,
    ) in enumerate(teacher_data):
        teacher, _ = Teacher.objects.get_or_create(
            employee_id = employee_id,
            defaults = {
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "phone_number": f"+9230010000{index + 1:02d}",
                "department": departments[index],
                "designation": teacher_designations[index],
                "qualification": teacher_qualifications[index],
                "gender": gender,
                "date_of_birth": date(
                    1978 + index,
                    1 + (index % 12),
                    10 + index,
                ),
                "date_of_joining": date(
                    2010 + (index % 10),
                    8,
                    1,
                ),
                "salary": 85000 + (index * 5000),
                "address": "Karachi, Pakistan",
                "is_active": True,
            },
        )

        teachers.append(teacher)

    print(f"Teachers ready: {len(teachers)}")

    print("\nCreating students...")

    student_data = [
        ("Ali", "Raza", "ali.raza@student.edu", "M"),
        ("Bilal", "Ahmed", "bilal.ahmed@student.edu", "M"),
        ("Hamza", "Khan", "hamza.khan@student.edu", "M"),
        ("Usman", "Malik", "usman.malik@student.edu", "M"),
        ("Hassan", "Ali", "hassan.ali@student.edu", "M"),
        ("Danish", "Iqbal", "danish.iqbal@student.edu", "M"),
        ("Saad", "Hassan", "saad.hassan@student.edu", "M"),
        ("Talha", "Sheikh", "talha.sheikh@student.edu", "M"),
        ("Huzaifa", "Aslam", "huzaifa.aslam@student.edu", "M"),
        ("Zainab", "Farooq", "zainab.farooq@student.edu", "F"),
    ]

    students = []

    for index, (
        first_name,
        last_name,
        email,
        gender,
    ) in enumerate(student_data):
        student, _ = Student.objects.get_or_create(
            student_email = email,
            defaults = {
                "first_name": first_name,
                "last_name": last_name,
                "parents_phone_number": f"+9231010000{index + 1:02d}",
                "date_of_birth": date(
                    2002 + (index % 4),
                    1 + (index % 12),
                    10 + index,
                ),
                "gender": gender,
                "address": "Karachi, Pakistan",
                "student_group": f"CS-{2026 - (index % 3)}",
                "department": departments[index],
                "teacher": teachers[index],
                "is_active": True,
            },
        )

        students.append(student)

    print(f"Students ready: {len(students)}")

    print("\nCreating courses...")

    course_data = [
        ("Introduction to Programming", "CS101"),
        ("Object Oriented Programming", "CS201"),
        ("Database Systems", "CS301"),
        ("Data Structures", "CS202"),
        ("Web Engineering", "CS305"),
        ("Artificial Intelligence", "AI401"),
        ("Machine Learning", "AI402"),
        ("Software Engineering", "SE301"),
        ("Computer Networks", "CS304"),
        ("Calculus", "MATH101"),
    ]

    courses = []

    for index, (name, code) in enumerate(course_data):
        course, _ = Course.objects.get_or_create(
            code = code,
            defaults = {
                "name": name,
                "description": f"{name} course.",
                "credits": 3,
                "department": departments[index],
                "teacher": teachers[index],
                "is_active": True,
            },
        )

        courses.append(course)

    print(f"Courses ready: {len(courses)}")

    print("\nCreating course offerings...")

    offerings = []

    for index in range(10):
        offering, _ = CourseOffering.objects.get_or_create(
            course = courses[index],
            teacher = teachers[index],
            semester = "FALL",
            academic_year = 2026,
            section = "A",
            defaults = {
                "is_active": True,
            },
        )

        offerings.append(offering)

    print(f"Course offerings ready: {len(offerings)}")

    print("\nCreating enrollments...")

    enrollments = []

    # First 10 students are enrolled in their corresponding offering.
    for index in range(10):
        enrollment, _ = Enrollment.objects.get_or_create(
            student = students[index],
            course_offering = offerings[index],
            defaults = {
                "status": "ACTIVE",
            },
        )

        enrollments.append(enrollment)

    # Additional students enrolled in Calculus.
    for index in range(10):
        enrollment, _ = Enrollment.objects.get_or_create(
            student = students[index],
            course_offering = offerings[9],
            defaults = {
                "status": "ACTIVE",
            },
        )

        enrollments.append(enrollment)

    print(f"Enrollments ready: {len(enrollments)}")

    print("\nCreating attendance...")

    attendance_statuses = [
        "PRESENT",
        "PRESENT",
        "ABSENT",
        "PRESENT",
        "LATE",
        "PRESENT",
        "PRESENT",
        "ABSENT",
        "PRESENT",
        "LATE",
    ]

    attendance_count = 0

    for index, enrollment in enumerate(enrollments[:10]):
        attendance, _ = Attendance.objects.get_or_create(
            enrollment = enrollment,
            date = date(2026, 8, 10),
            defaults = {
                "status": attendance_statuses[index],
                "remarks": "",
            },
        )

        attendance_count += 1

    print(f"Attendance records ready: {attendance_count}")

    print("\n======================================")
    print("TEST DATA CREATED SUCCESSFULLY")
    print("======================================")

    print(f"Departments      : {Department.objects.count()}")
    print(f"Teachers         : {Teacher.objects.count()}")
    print(f"Students         : {Student.objects.count()}")
    print(f"Courses          : {Course.objects.count()}")
    print(f"Course Offerings : {CourseOffering.objects.count()}")
    print(f"Enrollments      : {Enrollment.objects.count()}")
    print(f"Attendance       : {Attendance.objects.count()}")

    print("\nSeed data complete.")

seed_data()