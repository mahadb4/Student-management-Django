from common.messages import Messages
from common.validators import CommonValidator
from course_offerings.models import CourseOffering
from courses.models import Course
from sections.models import Section
from teachers.models import Teacher


class CourseOfferingValidator:
    def validate(self, data):
        CommonValidator.validate_required(data, [
            "course",
            "teacher",
            "semester",
            "academic_year",
            "section",
        ])

        course_id = data["course"]
        teacher_id = data["teacher"]
        semester = data["semester"]
        academic_year = data["academic_year"]
        section_id = data["section"]

        course = Course.objects.filter(id = course_id, is_active = True).first()
        if not course:
            raise ValueError(Messages.INVALID_COURSE.format(course_id))

        if not Teacher.objects.filter(id = teacher_id, is_active = True).exists():
            raise ValueError(Messages.INVALID_TEACHER.format(teacher_id))

        section = Section.objects.filter(id = section_id, is_deleted = False, is_active = True).first()
        if not section:
            raise ValueError(Messages.INVALID_SECTION.format(section_id))

        if course.semester_number is not None and course.semester_number != section.semester_number:
            raise ValueError(Messages.COURSE_SECTION_SEMESTER_MISMATCH.format(course.semester_number, section.semester_number))

        if semester not in CourseOffering.Semester.values:
            raise ValueError(Messages.INVALID_SEMESTER.format(semester))

        CommonValidator.validate_positive_number(academic_year, "Academic year")