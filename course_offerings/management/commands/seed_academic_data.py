import datetime

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction

from departments.models import Department
from sections.models import Section
from courses.models import Course
from teachers.models import Teacher
from course_offerings.models import CourseOffering
from users.models import User

DEFAULT_PASSWORD = "Abcd1234"
ACADEMIC_YEAR = 2026
SEMESTER_TERM = CourseOffering.Semester.FALL

# CourseOffering ids that existed before this command was ever run (confirmed
# against the original data). Never retired, deactivated, or otherwise
# modified by this command under any circumstance, even if their teacher
# isn't in a curriculum course's subject-matched pool - this command only
# ever ADDS offerings alongside pre-existing data, it never cleans up data
# it didn't create itself.
PROTECTED_OFFERING_IDS = {1, 2, 3, 4, 5, 14, 15}

TARGET_DEPARTMENTS = [
    "Computer Science",
    "Software Engineering",
    "Artificial Intelligence",
    "Data Science",
    "Information Technology",
]

SEMESTER_NUMBER = 1

# code, name, owning department name, credits
SEMESTER_1_CURRICULUM = [
    ("CS101", "Introduction to Programming", "Computer Science", 3),
    ("MATH101", "Calculus", "Mathematics", 3),
    ("ENG101", "English / Communication", "Computer Science", 3),
    ("PST101", "Pakistan Studies", "Computer Science", 2),
    ("BC101", "Basic Computing", "Computer Science", 3),
]

SECTION_NAMES = ["A", "B", "C", "D"]

# Which department's existing active teachers are eligible to teach a given
# course, plus any new teachers to create (housed administratively under
# "home_department") if that pool ends up empty. Subject-matched, not
# section-department-matched: e.g. Calculus is always taught by Mathematics
# teachers regardless of which department's section it's offered into.
COURSE_TEACHER_POOLS = {
    "CS101": {
        "home_department": "Computer Science",
        "teachers": [
            ("Faisal", "Anwar", "faisal.anwar@university.edu"),
            ("Nadia", "Sheikh", "nadia.sheikh@university.edu"),
        ],
    },
    "BC101": {
        "home_department": "Computer Science",
        "teachers": [
            ("Faisal", "Anwar", "faisal.anwar@university.edu"),
            ("Nadia", "Sheikh", "nadia.sheikh@university.edu"),
        ],
    },
    "MATH101": {
        "home_department": "Mathematics",
        "teachers": [
            ("Zainab", "Iqbal", "zainab.iqbal@university.edu"),
        ],
    },
    "ENG101": {
        "home_department": "Computer Science",
        "teachers": [
            ("Sana", "Malik", "sana.malik@university.edu"),
        ],
    },
    "PST101": {
        "home_department": "Computer Science",
        "teachers": [
            ("Kamran", "Yousuf", "kamran.yousuf@university.edu"),
        ],
    },
}


class _DryRunPlaceholder:
    """Stand-in for a not-yet-created row during --apply-less preview runs."""

    pk = None

    def __init__(self, **display_fields):
        for key, value in display_fields.items():
            setattr(self, key, value)


class Command(BaseCommand):
    help = (
        "Seeds a coherent Semester 1 academic dataset (courses, subject-matched "
        "teachers, and course offerings) across Computer Science, Software "
        "Engineering, Artificial Intelligence, Data Science, and Information "
        "Technology so every existing active Semester-1 section in those "
        "departments has compatible course offerings. Each course is taught by "
        "teachers matched to its actual subject (e.g. Calculus by Mathematics "
        "teachers) rather than by whichever department the section belongs to. "
        "Idempotent - safe to rerun. Only ever retires redundant offerings it "
        "created itself in a prior run (e.g. a stale rotation pairing) once a "
        "correct replacement already exists alongside it - a fixed list of "
        "pre-existing offering ids (PROTECTED_OFFERING_IDS) is never touched "
        "under any circumstance. Reuses existing Departments/Sections/Courses/"
        "Students by natural key. Defaults to a dry run - pass --apply to write changes."
    )

    def add_arguments(self, parser):
        parser.add_argument("--apply", action = "store_true", help = "Actually write changes (default: dry run).")

    def handle(self, *args, **options):
        apply = options["apply"]
        mode = "APPLYING" if apply else "DRY RUN (pass --apply to write changes)"
        self.stdout.write(self.style.WARNING(f"--- {mode} ---\n"))

        self.created = {"courses": 0, "teachers": 0, "offerings": 0, "users": 0}
        self.reused = {"courses": 0, "teachers": 0, "offerings": 0}
        self.retired = 0

        with transaction.atomic():
            departments = self._load_departments()
            courses = self._ensure_courses(departments, apply)
            teacher_pools = self._ensure_teacher_pools(departments, apply)
            self._ensure_offerings(departments, courses, teacher_pools, apply)
            self._retire_redundant_offerings(departments, courses, teacher_pools, apply)

            if not apply:
                transaction.set_rollback(True)

        self.stdout.write(self.style.SUCCESS(f"\n--- {mode} complete ---"))
        self.stdout.write(
            f"Courses: created {self.created['courses']}, reused {self.reused['courses']}\n"
            f"Teachers: created {self.created['teachers']}, reused {self.reused['teachers']}\n"
            f"Users: created {self.created['users']}\n"
            f"Course offerings: created {self.created['offerings']}, reused {self.reused['offerings']}, retired (mismatched) {self.retired}"
        )

    def _load_departments(self):
        departments = {}
        for name in TARGET_DEPARTMENTS + ["Mathematics"]:
            dept = Department.objects.filter(name = name, is_deleted = False).first()
            if not dept:
                self.stdout.write(self.style.ERROR(f"Missing expected department '{name}' - skipping anything dependent on it."))
                continue
            departments[name] = dept
        return departments

    def _ensure_courses(self, departments, apply):
        courses = {}
        for code, name, dept_name, credits in SEMESTER_1_CURRICULUM:
            dept = departments.get(dept_name)
            if not dept:
                continue

            course = Course.objects.filter(code = code).first()
            if course:
                self.reused["courses"] += 1
                self.stdout.write(f"  REUSE course {code} - {course.name} (dept {course.department.name})")
                if apply and course.semester_number != SEMESTER_NUMBER:
                    # Backfill only - this command owns this exact course code,
                    # so setting its semester classification here is safe and
                    # doesn't touch any course outside its own curriculum list.
                    course.semester_number = SEMESTER_NUMBER
                    course.save(update_fields = ["semester_number"])
            else:
                self.stdout.write(f"  CREATE course {code} - {name} (owning dept {dept_name}, semester {SEMESTER_NUMBER})")
                self.created["courses"] += 1
                course = _DryRunPlaceholder(code = code, name = name)
                if apply:
                    course = Course.objects.create(
                        name = name,
                        code = code,
                        credits = credits,
                        department = dept,
                        semester_number = SEMESTER_NUMBER,
                        is_active = True,
                    )
            courses[code] = course
        return courses

    def _ensure_teacher_pools(self, departments, apply):
        """
        Returns {course_code: [Teacher, ...]}, matched by subject via an
        explicit (name, email) seed list per course - never by querying a
        shared department, since multiple subject-specific teachers can be
        administratively housed under the same department without being
        interchangeable (e.g. an English teacher housed under Computer
        Science for lack of a dedicated department must not show up in
        CS101's pool).
        """
        pools = {}
        for code, pool_spec in COURSE_TEACHER_POOLS.items():
            home_dept = departments.get(pool_spec["home_department"])
            created_teachers = []
            for idx, (first, last, email) in enumerate(pool_spec["teachers"]):
                teacher = Teacher.objects.filter(email = email).first()
                if teacher:
                    self.reused["teachers"] += 1
                    created_teachers.append(teacher)
                    continue

                self.stdout.write(f"  CREATE teacher {first} {last} ({email}) for {code}, home dept {pool_spec['home_department']}")
                self.created["teachers"] += 1
                teacher = _DryRunPlaceholder(first_name = first, last_name = last)
                if apply and home_dept:
                    teacher = Teacher.objects.create(
                        first_name = first,
                        last_name = last,
                        employee_id = f"EMP-{home_dept.code}-{code}-{idx + 1:03d}",
                        email = email,
                        phone_number = "0000000000",
                        department = home_dept,
                        designation = "Lecturer",
                        qualification = "MS",
                        gender = "M",
                        date_of_birth = datetime.date(1985, 1, 1),
                        salary = 100000,
                        is_active = True,
                    )
                    self._ensure_user_for(teacher, "email", f"{first} {last}", "teacher", apply)
                created_teachers.append(teacher)

            pools[code] = created_teachers
        return pools

    def _ensure_user_for(self, profile, email_field, display_name, role, apply):
        email = getattr(profile, email_field)
        user = User.objects.filter(email__iexact = email).first()
        if not user:
            self.created["users"] += 1
            if apply:
                user = User.objects.create_user(
                    email = email,
                    name = display_name,
                    password = DEFAULT_PASSWORD,
                    role = role,
                    status = "approved",
                )
                group, _ = Group.objects.get_or_create(name = role.upper())
                user.groups.add(group)
        if apply and user and not profile.user_id:
            profile.user = user
            profile.save(update_fields = ["user"])

    def _target_sections(self, dept):
        return list(
            Section.objects.filter(
                department = dept,
                semester_number = 1,
                academic_year = ACADEMIC_YEAR,
                is_active = True,
                is_deleted = False,
                name__in = SECTION_NAMES,
            ).order_by("name")
        )

    def _retire_redundant_offerings(self, departments, courses, teacher_pools, apply):
        """
        Cleans up offerings for this command's own curriculum courses +
        target sections, but ONLY ever removes redundancy - it never retires
        the sole/last remaining offering for a given course+section, so a
        pre-existing offering this command didn't create is left alone
        unless a subject-matched replacement already exists alongside it
        (created by _ensure_offerings, which must run before this method).
        For each course+section with 2+ live offerings, keeps the ones whose
        teacher is in that course's valid subject pool and retires the rest;
        if none has a valid-pool teacher, nothing is touched at all.
        """
        for code, _, _, _ in SEMESTER_1_CURRICULUM:
            course = courses.get(code)
            if not course or not course.pk:
                continue

            valid_teacher_ids = {t.pk for t in teacher_pools.get(code, []) if t.pk}
            if not valid_teacher_ids:
                continue

            for dept_name in TARGET_DEPARTMENTS:
                dept = departments.get(dept_name)
                if not dept:
                    continue
                sections = self._target_sections(dept)
                for section in sections:
                    live = list(
                        CourseOffering.objects.filter(
                            course = course,
                            semester = SEMESTER_TERM,
                            academic_year = ACADEMIC_YEAR,
                            section = section,
                            is_deleted = False,
                        ).exclude(id__in = PROTECTED_OFFERING_IDS).order_by("id")
                    )
                    if len(live) < 2:
                        continue

                    valid_ones = [o for o in live if o.teacher_id in valid_teacher_ids]
                    if not valid_ones:
                        continue

                    keep_ids = {valid_ones[0].id}
                    for offering in live:
                        if offering.id in keep_ids:
                            continue
                        self.stdout.write(
                            f"  RETIRE redundant offering #{offering.id} {code} -> {dept_name} "
                            f"Sem1 {section.name} (teacher {offering.teacher}, keeping #{valid_ones[0].id})"
                        )
                        self.retired += 1
                        if apply:
                            offering.is_active = False
                            offering.is_deleted = True
                            offering.save(update_fields = ["is_active", "is_deleted"])

    def _ensure_offerings(self, departments, courses, teacher_pools, apply):
        for dept_name in TARGET_DEPARTMENTS:
            dept = departments.get(dept_name)
            if not dept:
                continue

            sections = self._target_sections(dept)
            if not sections:
                self.stdout.write(self.style.WARNING(f"  No active Semester 1 / {ACADEMIC_YEAR} sections found for {dept_name} - skipping."))
                continue

            for code, _, _, _ in SEMESTER_1_CURRICULUM:
                course = courses.get(code)
                if not course:
                    continue

                teachers = teacher_pools.get(code) or []
                if not teachers:
                    self.stdout.write(self.style.WARNING(f"  No teacher pool available for {code} - skipping its offerings."))
                    continue

                for idx, section in enumerate(sections):
                    teacher = teachers[idx % len(teachers)]

                    # Reuse ANY existing offering for this course+section taught
                    # by a teacher already in this course's valid pool, not just
                    # the one the rotation would currently pick - the rotation
                    # index is only a tie-breaker for which *new* teacher to
                    # assign, not a key to match on, since queryset order for
                    # rebuilding the pool isn't guaranteed identical to a
                    # previous run's.
                    offering = None
                    if course.pk:
                        valid_ids = [t.pk for t in teachers if t.pk]
                        offering = CourseOffering.objects.filter(
                            course = course,
                            teacher_id__in = valid_ids,
                            semester = SEMESTER_TERM,
                            academic_year = ACADEMIC_YEAR,
                            section = section,
                            is_deleted = False,
                        ).order_by("id").first()

                    if offering:
                        self.reused["offerings"] += 1
                        continue

                    self.stdout.write(
                        f"  CREATE offering {code} -> {dept_name} Sem1 {section.name} "
                        f"(teacher {teacher.first_name} {teacher.last_name})"
                    )
                    self.created["offerings"] += 1
                    if apply:
                        CourseOffering.objects.create(
                            course = course,
                            teacher = teacher,
                            semester = SEMESTER_TERM,
                            academic_year = ACADEMIC_YEAR,
                            section = section,
                            is_active = True,
                        )
