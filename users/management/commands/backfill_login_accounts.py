from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction
from users.models import User
from students.models import Student
from teachers.models import Teacher

DEFAULT_PASSWORD = "Abcd1234"


class Command(BaseCommand):
    help = (
        "Backfills login access for Student/Teacher records created before "
        "authentication existed, and for approved users missing their role "
        "Group. Additive only: never overwrites an existing password, an "
        "existing Student/Teacher<->User link, or an existing Group "
        "membership. Defaults to a dry run - pass --apply to write changes."
    )

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Actually write changes (default: dry run).")
        parser.add_argument("--password", type=str, default=DEFAULT_PASSWORD, help=f"Password for newly created accounts (default: {DEFAULT_PASSWORD}).")

    def handle(self, *args, **options):
        apply = options["apply"]
        password = options["password"]
        mode = "APPLYING" if apply else "DRY RUN (pass --apply to write changes)"
        self.stdout.write(self.style.WARNING(f"--- {mode} ---\n"))

        with transaction.atomic():
            self._backfill_entity(Student, "student", "student_email", password, apply)
            self._backfill_entity(Teacher, "teacher", "email", password, apply)
            self._backfill_groups(password, apply)

        self.stdout.write(self.style.SUCCESS(f"\n--- {mode} complete ---"))

    def _backfill_entity(self, model, role, email_field, password, apply):
        label = model.__name__
        unlinked = model.objects.filter(user__isnull=True)
        self.stdout.write(f"{label}: {unlinked.count()} record(s) without a linked login account")

        for record in unlinked:
            email = getattr(record, email_field)
            user = User.objects.filter(email__iexact=email).first()

            if user:
                action = f"LINK existing user ({email}) to {label} #{record.id}"
            else:
                action = f"CREATE new user ({email}, role={role}, password={'*' * len(password)}) and link to {label} #{record.id}"

            self.stdout.write(f"  - {action}")

            if not apply:
                continue

            if not user:
                user = User.objects.create_user(
                    email=email,
                    name=f"{record.first_name} {record.last_name}".strip(),
                    password=password,
                    role=role,
                    status="approved",
                )
            elif not user.has_usable_password():
                # Existing user shell with no real password (e.g. created via
                # data migration/admin without one) - safe to set a usable one.
                user.set_password(password)
                user.save(update_fields=["password"])

            record.user = user
            record.save(update_fields=["user"])

    def _backfill_groups(self, password, apply):
        # status__iexact: a handful of pre-existing rows have "APPROVED" (uppercase),
        # inconsistent with the app's own lowercase convention - matched here rather
        # than rewritten, since correcting stored casing isn't this command's job.
        approved_without_group = User.objects.filter(status__iexact="approved").exclude(groups__isnull=False).distinct()
        self.stdout.write(f"\nApproved users missing their role Group: {approved_without_group.count()}")

        for user in approved_without_group:
            self.stdout.write(f"  - ADD {user.email} to group '{user.role.upper()}'")

            if not apply:
                continue

            group, _ = Group.objects.get_or_create(name=user.role.upper())
            user.groups.add(group)
