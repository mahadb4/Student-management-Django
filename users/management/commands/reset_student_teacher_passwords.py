from django.core.management.base import BaseCommand
from users.models import User

TEMP_PASSWORD = "Abcd.1234"


class Command(BaseCommand):
    help = (
        "TESTING ONLY: resets the password for every Student/Teacher login "
        f"account to a shared temporary password ({TEMP_PASSWORD}), using "
        "set_password() for proper hashing. Strictly scoped to role in "
        "(student, teacher) - never touches admin or staff accounts. "
        "Defaults to a dry run - pass --apply to write changes."
    )

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Actually write changes (default: dry run).")

    def handle(self, *args, **options):
        apply = options["apply"]
        mode = "APPLYING" if apply else "DRY RUN (pass --apply to write changes)"
        self.stdout.write(self.style.WARNING(f"--- {mode} ---\n"))

        users = User.objects.filter(role__in=["student", "teacher"]).order_by("role", "email")
        self.stdout.write(f"Accounts targeted (role student/teacher): {users.count()}\n")

        changed = 0
        for user in users:
            self.stdout.write(f"  - RESET {user.email} (role={user.role})")
            changed += 1

            if not apply:
                continue

            user.set_password(TEMP_PASSWORD)
            user.save(update_fields=["password"])

        excluded = User.objects.exclude(role__in=["student", "teacher"]).count()
        self.stdout.write(f"\nAccounts excluded (admin/staff/other roles, untouched): {excluded}")
        self.stdout.write(self.style.SUCCESS(
            f"\n--- {mode} complete: {changed} account(s) {'reset' if apply else 'would be reset'} ---"
        ))
