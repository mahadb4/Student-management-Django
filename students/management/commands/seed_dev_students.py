import datetime

from django.core.management.base import BaseCommand
from django.db import transaction

from common.cache.cache_service import CacheService
from course_offerings.models import CourseOffering
from departments.models import Department
from enrollments.cache.enrollment_cache import EnrollmentCache
from enrollments.models import Enrollment
from enrollments.repositories.enrollment_repository import EnrollmentRepository
from enrollments.services.enrollment_service import EnrollmentService
from enrollments.services.enrollment_validator import EnrollmentValidator
from sections.models import Section
from students.cache.student_cache import StudentCache
from students.models import Student
from students.repositories.student_repository import StudentRepository
from students.services.student_service import StudentService
from students.services.student_validator import StudentValidator
from users.management.commands.reset_student_teacher_passwords import TEMP_PASSWORD
from users.models import User

# Synthetic development/test accounts only. dev.example.com is an RFC 2606
# reserved domain, so these addresses can never reach a real mailbox - and the
# prefix makes every seeded account trivially identifiable (and re-detectable
# on a second run, which is what makes this command idempotent).
EMAIL_PREFIX = "cs.dev.student"
EMAIL_DOMAIN = "dev.example.com"

DEPARTMENT_NAME = "Computer Science"
ACADEMIC_YEAR = 2026
SEMESTER_TERM = CourseOffering.Semester.FALL

# The project's own definition of the first-semester curriculum, copied from
# course_offerings/management/commands/seed_academic_data.py's
# SEMESTER_1_CURRICULUM rather than invented here.
SEMESTER_1_COURSE_CODES = ["CS101", "MATH101", "ENG101", "PST101", "BC101"]

# Additionally offered to whichever section has it (currently only Section D,
# taught by Muhammad Owais) - it is a semester_number = 1 course like the rest.
EXTRA_COURSE_CODES = ["1010"]

# How many new students land in each section. Section D is weighted so the
# Section-D teacher's roster is big enough to be worth testing against.
SECTION_DISTRIBUTION = [("A", 7), ("B", 7), ("C", 6), ("D", 10)]

# Several courses have more than one active offering in the same section,
# taught by different teachers (e.g. Section D has both this teacher's BC101
# and another teacher's BC101). A student must only ever be enrolled in one of
# them, so when there is a choice the offering belonging to this teacher wins -
# that is what makes his roster, and therefore the Assignments/Remarks/
# Attendance screens, worth testing. Overridable via --prefer-teacher-email.
PREFERRED_TEACHER_EMAIL = "mowais@gmail.com"

# (first name, last name, gender) - realistic-looking but synthetic; paired
# with the reserved-domain emails above so they are unambiguously test data.
STUDENT_NAMES = [
    # "Bilal Sarfraz"/"Danish Mukhtar" (not Ahmed/Iqbal) because real students
    # with those names already exist in other departments - see
    # fix_dev_student_emails.NAME_OVERRIDES.
    ("Hassan", "Raza", "M"), ("Fatima", "Noor", "F"), ("Bilal", "Sarfraz", "M"),
    ("Zara", "Khan", "F"), ("Usman", "Tariq", "M"), ("Hira", "Aslam", "F"),
    ("Danish", "Mukhtar", "M"), ("Maryam", "Shah", "F"), ("Talha", "Javed", "M"),
    ("Nimra", "Saeed", "F"), ("Ahsan", "Malik", "M"), ("Areeba", "Farooq", "F"),
    ("Saad", "Rehman", "M"), ("Iqra", "Hussain", "F"), ("Hamza", "Qureshi", "M"),
    ("Laiba", "Anwar", "F"), ("Umair", "Bashir", "M"), ("Mehwish", "Zafar", "F"),
    ("Faizan", "Sattar", "M"), ("Amna", "Rashid", "F"), ("Shahzaib", "Younis", "M"),
    ("Rabia", "Kamal", "F"), ("Arsalan", "Ghani", "M"), ("Sana", "Waheed", "F"),
    ("Zeeshan", "Abbas", "M"), ("Komal", "Nawaz", "F"), ("Waleed", "Siddique", "M"),
    ("Anum", "Yousaf", "F"), ("Kashif", "Mehmood", "M"), ("Tehreem", "Akhtar", "F"),
    ("Rehan", "Aziz", "M"), ("Sadia", "Rauf", "F"), ("Noman", "Ashraf", "M"),
    ("Eman", "Riaz", "F"), ("Junaid", "Saleem", "M"), ("Warda", "Hanif", "F"),
    ("Adnan", "Shafiq", "M"), ("Bushra", "Munir", "F"), ("Imran", "Latif", "M"),
    ("Saba", "Ilyas", "F"), ("Asad", "Bhatti", "M"), ("Ayesha", "Sohail", "F"),
    ("Owais", "Nadeem", "M"), ("Sidra", "Waqas", "F"), ("Fahad", "Zubair", "M"),
    ("Kiran", "Arif", "F"), ("Salman", "Haider", "M"), ("Mahnoor", "Jamil", "F"),
    ("Hammad", "Rafiq", "M"), ("Nida", "Shahid", "F"),
]


class Command(BaseCommand):
    help = (
        "DEVELOPMENT/TEST DATA ONLY: creates synthetic Computer Science students "
        "and enrols them in their own section's existing first-semester course "
        "offerings. Every record is created through the real StudentService / "
        "EnrollmentService, so all existing business rules (section matching, "
        "duplicate enrolment, active/deleted checks, approval + STUDENT group) "
        "are enforced exactly as they are for the HTTP API. Idempotent: students "
        f"are keyed on their {EMAIL_PREFIX}NN@{EMAIL_DOMAIN} email and reused if "
        "they already exist. Defaults to a dry run - pass --apply to write changes."
    )

    def add_arguments(self, parser):
        parser.add_argument("--apply", action = "store_true", help = "Actually write changes (default: dry run).")
        parser.add_argument("--count", type = int, default = 30, help = "How many synthetic students to ensure exist (default: 30).")
        parser.add_argument(
            "--prefer-teacher-email", default = PREFERRED_TEACHER_EMAIL,
            help = (
                "When a course already has more than one offering in the same section "
                "(different teachers), enrol students in this teacher's offering. Only "
                "affects which existing offering is chosen - never reassigns a teacher."
            ),
        )

    def handle(self, *args, **options):
        apply = options["apply"]
        count = options["count"]
        self.preferred_teacher_email = options["prefer_teacher_email"]
        mode = "APPLYING" if apply else "DRY RUN (pass --apply to write changes)"
        self.stdout.write(self.style.WARNING(f"--- {mode} ---\n"))

        if count > len(STUDENT_NAMES):
            self.stdout.write(self.style.ERROR(
                f"--count {count} exceeds the {len(STUDENT_NAMES)} available synthetic names. Aborting."
            ))
            return

        self.created = {"students": 0, "enrollments": 0}
        self.reused = {"students": 0, "enrollments": 0}
        self.skipped = []

        # Wired exactly as students/api/student_api.py and
        # enrollments/api/enrollment_api.py wire them, so this command runs the
        # same validation path as the real endpoints.
        student_service = StudentService(StudentValidator(), StudentRepository(), StudentCache(CacheService()))
        enrollment_service = EnrollmentService(EnrollmentValidator(), EnrollmentRepository(), EnrollmentCache(CacheService()))

        with transaction.atomic():
            department = Department.objects.filter(name = DEPARTMENT_NAME, is_deleted = False).first()
            if not department:
                self.stdout.write(self.style.ERROR(f"Department '{DEPARTMENT_NAME}' not found. Aborting."))
                return

            section_plan = self._build_section_plan(department, count)
            course_plans = {name: self._course_plan_for_section(section) for name, section in section_plan.items()}
            self._report_course_plans(course_plans)

            index = 0
            for section_name, section in section_plan.items():
                for _ in range(self._quota(section_name, count)):
                    student = self._ensure_student(student_service, index, department, section, apply)
                    self._ensure_enrollments(enrollment_service, student, course_plans[section_name], index, apply)
                    index += 1

            if not apply:
                transaction.set_rollback(True)

        self.stdout.write(self.style.SUCCESS(f"\n--- {mode} complete ---"))
        self.stdout.write(
            f"Students: created {self.created['students']}, reused {self.reused['students']}\n"
            f"Enrollments: created {self.created['enrollments']}, reused {self.reused['enrollments']}"
        )
        for message in self.skipped:
            self.stdout.write(self.style.WARNING(f"  SKIPPED: {message}"))

    def _quota(self, section_name, count):
        # Scale the fixed A/B/C/D distribution to the requested --count.
        total = sum(quota for _, quota in SECTION_DISTRIBUTION)
        quotas = {}
        assigned = 0
        for name, quota in SECTION_DISTRIBUTION[:-1]:
            quotas[name] = round(quota * count / total)
            assigned += quotas[name]
        quotas[SECTION_DISTRIBUTION[-1][0]] = count - assigned
        return quotas[section_name]

    def _build_section_plan(self, department, count):
        plan = {}
        for name, _ in SECTION_DISTRIBUTION:
            section = Section.objects.filter(
                department = department, name = name, academic_year = ACADEMIC_YEAR,
                is_active = True, is_deleted = False,
            ).first()
            if not section:
                self.stdout.write(self.style.ERROR(f"Section '{name}' not found in {DEPARTMENT_NAME} - skipping it."))
                continue
            plan[name] = section
        return plan

    def _course_plan_for_section(self, section):
        """
        The offerings a student in this section should be enrolled in: one per
        first-semester course code, read from the offerings that already exist
        in the database. Where a course has more than one offering in the same
        section (different teachers), exactly one is picked so a student is
        never enrolled in the same course twice.
        """
        plan = []
        for code in SEMESTER_1_COURSE_CODES + EXTRA_COURSE_CODES:
            offerings = list(CourseOffering.objects.filter(
                section = section, course__code = code, is_active = True, is_deleted = False,
                semester = SEMESTER_TERM, academic_year = ACADEMIC_YEAR,
                course__is_active = True, teacher__is_active = True,
            ).select_related("course", "teacher__user").order_by("id"))

            if not offerings:
                continue

            preferred = [
                o for o in offerings
                if o.teacher.user.email.lower() == self.preferred_teacher_email.lower()
            ]
            plan.append(preferred[0] if preferred else offerings[0])

        return plan

    def _report_course_plans(self, course_plans):
        self.stdout.write("Course plan per section (derived from existing offerings):")
        for section_name, plan in course_plans.items():
            self.stdout.write(f"  Section {section_name}: " + ", ".join(
                f"{o.course.code}({o.teacher.user.name})" for o in plan
            ))
        self.stdout.write("")

    def _email_for(self, index):
        return f"{EMAIL_PREFIX}{index + 1:02d}@{EMAIL_DOMAIN}"

    def _phone_for(self, index):
        return f"0300{index + 1:07d}"

    def _find_existing(self, index):
        """
        Locate a previously seeded student. Keyed on the deterministic
        parents_phone_number rather than the email, because
        fix_dev_student_emails renames these accounts to first.last@student.edu
        afterwards - matching on email alone would miss them and this command
        would then create a second copy of all 30 on its next run.
        """
        return Student.objects.filter(parents_phone_number = self._phone_for(index)).first()

    def _ensure_student(self, student_service, index, department, section, apply):
        email = self._email_for(index)
        existing = self._find_existing(index)

        if existing:
            self.reused["students"] += 1
            return existing

        first_name, last_name, gender = STUDENT_NAMES[index]
        self.stdout.write(f"  CREATE student {first_name} {last_name} <{email}> section {section.name}")
        self.created["students"] += 1

        if not apply:
            return None

        student = student_service.create({
            "first_name": first_name,
            "last_name": last_name,
            "student_email": email,
            "parents_phone_number": self._phone_for(index),
            # Deterministic, ~19-20 years old - comfortably past the
            # StudentValidator minimum-age rule.
            "date_of_birth": datetime.date(2006, (index % 12) + 1, (index % 28) + 1),
            "gender": gender,
            "address": f"House {index + 1}, Test Colony",
            "department": department.id,
            "section": section.id,
            "is_active": True,
        })

        # StudentService.create() sets its own default password; re-set it to
        # the project's shared dev password via the same set_password() path
        # users/management/commands/reset_student_teacher_passwords.py uses, so
        # every seeded account logs in with the same credentials as the other
        # dev student/teacher accounts.
        user = student.user
        user.set_password(TEMP_PASSWORD)
        user.save(update_fields = ["password"])

        return student

    def _ensure_enrollments(self, enrollment_service, student, course_plan, index, apply):
        # Light, deterministic variation so the cohort isn't a perfect
        # copy-paste: every 7th student is missing their last course, the way a
        # real roster has a few incomplete enrolments.
        offerings = course_plan[:-1] if index % 7 == 6 else course_plan

        for offering in offerings:
            if not apply:
                self.created["enrollments"] += 1
                continue

            if Enrollment.objects.filter(student = student, course_offering = offering).exists():
                self.reused["enrollments"] += 1
                continue

            try:
                enrollment_service.create({
                    "student": student.id,
                    "course_offering": offering.id,
                    "status": Enrollment.Status.ACTIVE,
                })
                self.created["enrollments"] += 1
            except ValueError as e:
                # A business rule rejected it (e.g. section mismatch). Never
                # force the row in - report it and move on.
                self.skipped.append(f"{student.user.email} -> {offering.course.code} (offering {offering.id}): {e}")
