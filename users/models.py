from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from common.messages import Messages


class UserManager(BaseUserManager):
    def create_user(self, email, name, password = None, role = "student", status = "pending"):
        if not email:
            raise ValueError(Messages.EMAIL_REQUIRED)

        user = self.model(
            email = self.normalize_email(email),
            name = name,
            role = role,
            status = status,
        )

        user.set_password(password)
        user.save(using = self._db)

        return user

    def create_superuser(self, email, name, password = None):
        user = self.create_user(
            email = email,
            name = name,
            password = password,
            role = "admin",
            status = "approved",
        )

        user.is_staff = True
        user.is_superuser = True
        user.save(using = self._db)

        return user


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ("admin", "Admin"),
        ("student", "Student"),
        ("teacher", "Teacher"),
        ("staff", "Staff"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    name = models.CharField(max_length = 255)
    email = models.EmailField(unique = True)
    role = models.CharField(max_length = 20, choices = ROLE_CHOICES, default = "student")
    status = models.CharField(max_length = 20, choices = STATUS_CHOICES, default = "pending")
    is_active = models.BooleanField(default = True)
    is_staff = models.BooleanField(default = False)
    created_at = models.DateTimeField(auto_now_add = True)
    updated_at = models.DateTimeField(auto_now = True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    def __str__(self):
        return self.email