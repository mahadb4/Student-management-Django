import getpass
from django.core.management.base import BaseCommand, CommandError
from users.models import User


class Command(BaseCommand):
    help = (
        "Securely creates an admin user. "
        "Admin accounts cannot be created through public registration."
    )

    def add_arguments(self, parser):
        parser.add_argument("--email", type = str, help = "Admin email address")
        parser.add_argument("--name", type = str, help = "Admin full name")
        parser.add_argument(
            "--password",
            type = str,
            help = "Admin password (omit to be prompted securely)",
        )

    def handle(self, *args, **options):
        email = options.get("email")
        name = options.get("name")
        password = options.get("password")

        if not email:
            email = input("Email: ").strip()
        if not name:
            name = input("Full name: ").strip()
        if not password:
            password = getpass.getpass("Password: ")
            confirm = getpass.getpass("Confirm password: ")
            if password != confirm:
                raise CommandError("Passwords do not match.")

        if not email:
            raise CommandError("Email is required.")
        if not name:
            raise CommandError("Name is required.")
        if not password or len(password) < 8:
            raise CommandError("Password must be at least 8 characters.")

        if User.objects.filter(email__iexact = email).exists():
            raise CommandError(f"A user with email '{email}' already exists.")

        user = User.objects.create_superuser(
            email = email,
            name = name,
            password = password,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Admin user created successfully.\n"
                f"  Name  : {user.name}\n"
                f"  Email : {user.email}\n"
                f"  Role  : {user.role}\n"
                f"  Status: {user.status}"
            )
        )