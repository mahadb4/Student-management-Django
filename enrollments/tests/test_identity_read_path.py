from datetime import date
from django.test import TestCase
from attendance.mappers.attendance_mapper import AttendanceMapper
from attendance.models import Attendance
from attendance.repositories.attendance_repository import AttendanceRepository
from courses.mappers.course_mapper import CourseMapper
from courses.models import Course
from courses.repositories.course_repository import CourseRepository
from course_offerings.mappers.course_offering_mapper import CourseOfferingMapper
from course_offerings.models import CourseOffering
from course_offerings.repositories.course_offering_repository import CourseOfferingRepository
from departments.models import Department
from enrollments.mappers.enrollment_mapper import EnrollmentMapper
from enrollments.models import Enrollment
from enrollments.repositories.enrollment_repository import EnrollmentRepository
from sections.models import Section
from students.models import Student
from teachers.models import Teacher
from users.models import User


#Course/CourseOffering/Enrollment/Attendance display names via effective identity.
class TransitiveIdentityReadPathTests(TestCase):

    def setUp(self):
        self.department = Department.objects.create(name = "Computing", code = "CMP")
        self.section = Section.objects.create(
            name = "A", department = self.department, semester_number = 1, academic_year = 2026,
        )

        self.student_user = User.objects.create_user(
            email = "student@example.com", name = "Linked Student", password = "x", role = "student",
        )
        self.student = Student.objects.create(
            user = self.student_user, parents_phone_number = "1234567",
            department = self.department, section = self.section,
        )

        self.teacher_user = User.objects.create_user(
            email = "teacher@example.com", name = "Linked Teacher", password = "x", role = "teacher",
        )
        self.teacher = Teacher.objects.create(
            user = self.teacher_user,
            employee_id = "E1", phone_number = "1234567",
            department = self.department, designation = "Lecturer", qualification = "MSc",
            date_of_joining = date(2020, 1, 1), salary = 1,
        )

        self.course = Course.objects.create(
            name = "Algorithms", code = "CS101", credits = 3,
            department = self.department, teacher = self.teacher,
        )
        self.offering = CourseOffering.objects.create(
            course = self.course, teacher = self.teacher, semester = CourseOffering.Semester.FALL,
            academic_year = 2026, section = self.section,
        )
        self.enrollment = Enrollment.objects.create(student = self.student, course_offering = self.offering)
        self.attendance = Attendance.objects.create(
            enrollment = self.enrollment, date = date(2026, 1, 1), status = Attendance.Status.PRESENT,
        )

    def test_course_teacher_name_uses_effective_identity(self):
        course = CourseRepository().get_queryset_for_list().get(id = self.course.id)
        dto = CourseMapper.to_list_dto(course)
        self.assertEqual(dto["teacher_name"], "Linked Teacher")

    def test_course_offering_teacher_name_uses_effective_identity(self):
        offering = CourseOfferingRepository().get_queryset_for_list().get(id = self.offering.id)
        dto = CourseOfferingMapper.to_list_dto(offering)
        self.assertEqual(dto["teacher_name"], "Linked Teacher")

    def test_course_offering_search_matches_linked_teacher_user_fields(self):
        results = CourseOfferingRepository().get_queryset_for_list(search = "Linked Teacher")
        self.assertIn(self.offering.id, results.values_list("id", flat = True))

    def test_enrollment_student_and_teacher_name_use_effective_identity(self):
        enrollment = EnrollmentRepository().get_queryset_for_list().get(id = self.enrollment.id)
        list_dto = EnrollmentMapper.to_list_dto(enrollment)
        self.assertEqual(list_dto["student_name"], "Linked Student")
        self.assertEqual(list_dto["student_email"], "student@example.com")

        teacher_dto = EnrollmentMapper.to_teacher_list_dto(enrollment)
        self.assertEqual(teacher_dto["student_name"], "Linked Student")

        student_dto = EnrollmentMapper.to_student_list_dto(enrollment)
        self.assertEqual(student_dto["teacher_name"], "Linked Teacher")

    def test_enrollment_search_matches_linked_student_user_fields(self):
        results = EnrollmentRepository().get_queryset_for_list(search = "Linked Student")
        self.assertIn(self.enrollment.id, results.values_list("id", flat = True))

    def test_attendance_student_name_uses_effective_identity(self):
        # AttendanceMapper.to_teacher_list_dto() no longer carries student_name
        # at all (the Attendance page maps enrollment_id -> student via a
        # separate roster fetch instead - see attendance_mapper.py) - only
        # the admin-facing to_list_dto still resolves an identity-derived name.
        attendance = AttendanceRepository().get_queryset_for_list().get(id = self.attendance.id)
        dto = AttendanceMapper.to_list_dto(attendance)
        self.assertEqual(dto["student_name"], "Linked Student")
