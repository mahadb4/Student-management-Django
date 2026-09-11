from django.core.management.base import BaseCommand
from django.db import transaction

from common.cache.cache_service import CacheService
from students.cache.student_cache import StudentCache
from students.models import Student
from users.models import User

# The seed-time email pattern written by seed_dev_students - the only accounts
# this command will ever touch.
LEGACY_EMAIL_PREFIX = "cs.dev.student"
NEW_EMAIL_DOMAIN = "student.edu"

# Two synthetic students were generated with names that coincidentally match
# real pre-existing students in other departments (Bilal Ahmed - Business
# Administration, Danish Iqbal - Electrical Engineering), so first.last@ would
# have collided with those real accounts. These synthetic students are renamed
# instead, so their derived email is naturally unique. Keyed by seed email so
# this stays exact and re-runnable; the same names are mirrored in
# seed_dev_students.STUDENT_NAMES.
NAME_OVERRIDES = {
    "cs.dev.student03@dev.example.com": ("Bilal", "Sarfraz"),
    "cs.dev.student07@dev.example.com": ("Danish", "Mukhtar"),
}


def derive_email(first, last):
    """first.last@student.edu, matching the convention the pre-existing
    students already use (e.g. ayesha.raza@student.edu)."""
    return f"{first.strip().lower()}.{last.strip().lower()}@{NEW_EMAIL_DOMAIN}"


def target_name(student):
    """The name this student should end up with: its current one, unless it is
    one of the two deliberately renamed above."""
    override = NAME_OVERRIDES.get(student.user.email.lower())
    if override:
        return override
    return student.effective_first_name, student.effective_last_name


class Command(BaseCommand):
    help = (
        "Renames the synthetic students created by seed_dev_students from their "
        f"{LEGACY_EMAIL_PREFIX}NN@... seed addresses to the project's normal "
        f"first.last@{NEW_EMAIL_DOMAIN} convention. Only the email changes - names, "
        "sections, enrollments, passwords and every other field are left untouched. "
        "Aborts without writing anything if any derived email would collide with "
        "another account (pass --skip-collisions to rename only the safe ones). "
        "Defaults to a dry run - pass --apply to write changes."
    )

    def add_arguments(self, parser):
        parser.add_argument("--apply", action = "store_true", help = "Actually write changes (default: dry run).")
        parser.add_argument(
            "--skip-collisions", action = "store_true",
            help = "Rename only the non-colliding students instead of aborting the whole run.",
        )

    def handle(self, *args, **options):
        apply = options["apply"]
        skip_collisions = options["skip_collisions"]
        mode = "APPLYING" if apply else "DRY RUN (pass --apply to write changes)"
        self.stdout.write(self.style.WARNING(f"--- {mode} ---\n"))

        students = list(
            Student.objects.filter(user__email__istartswith = LEGACY_EMAIL_PREFIX)
            .select_related("user").order_by("user__email")
        )

        if not students:
            self.stdout.write(self.style.SUCCESS(
                f"No accounts matching {LEGACY_EMAIL_PREFIX}* found - nothing to do "
                "(already renamed, or none were ever seeded)."
            ))
            return

        self.stdout.write(f"Synthetic students found: {len(students)}\n")

        planned = []      # (student, new_name_or_None, new_email)
        collisions = []   # (student, new_email, reason)
        seen = {}

        for student in students:
            first, last = target_name(student)
            new_email = derive_email(first, last)
            renamed_to = f"{first} {last}" if student.user.name != f"{first} {last}" else None

            if new_email in seen:
                collisions.append((student, new_email, f"same derived email as {seen[new_email]}"))
                continue

            clash = User.objects.filter(email__iexact = new_email).exclude(id = student.user_id).first()
            if clash:
                collisions.append((student, new_email, f"already used by existing {clash.role} (user id {clash.id})"))
                continue

            seen[new_email] = student.user.email
            planned.append((student, renamed_to, new_email))

        # ── Report ───────────────────────────────────────────────────────────
        self.stdout.write(f"{'Student Name':<24} {'Old Email':<34} {'New Email'}")
        self.stdout.write("-" * 92)
        for student, renamed_to, new_email in planned:
            name_cell = student.user.name if not renamed_to else f"{student.user.name} -> {renamed_to}"
            self.stdout.write(f"{name_cell:<24} {student.user.email:<34} {new_email}")

        if collisions:
            self.stdout.write("")
            self.stdout.write(self.style.ERROR(f"COLLISIONS ({len(collisions)}) - these would create duplicate emails:"))
            for student, new_email, reason in collisions:
                self.stdout.write(self.style.ERROR(
                    f"  {student.user.name:<24} {student.user.email:<34} -> {new_email}  [{reason}]"
                ))

            if not skip_collisions:
                self.stdout.write("")
                self.stdout.write(self.style.ERROR(
                    "ABORTED - nothing was written. Resolve the collisions above, or re-run "
                    "with --skip-collisions to rename only the safe accounts."
                ))
                return

            self.stdout.write(self.style.WARNING(
                f"\n--skip-collisions set: leaving the {len(collisions)} colliding account(s) on their seed email."
            ))

        if not apply:
            self.stdout.write(self.style.SUCCESS(
                f"\n--- {mode} complete: {len(planned)} account(s) would be renamed ---"
            ))
            return

        cache = StudentCache(CacheService())
        with transaction.atomic():
            for student, renamed_to, new_email in planned:
                user = student.user
                # Only email (and, for the two documented NAME_OVERRIDES, name)
                # is written - section, enrollments, password and everything
                # else are deliberately untouched.
                user.email = new_email
                fields = ["email"]

                if renamed_to:
                    user.name = renamed_to
                    fields.append("name")

                user.save(update_fields = fields)
                cache.invalidate_on_write(student.id)

        self.stdout.write(self.style.SUCCESS(
            f"\n--- {mode} complete: {len(planned)} account(s) renamed, {len(collisions)} skipped ---"
        ))
