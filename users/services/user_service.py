from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from common.messages import Messages


class UserService:
    def __init__(self, validator, repository):
        self.validator = validator
        self.repository = repository

    def get(self, user_id):
        return self.repository.get(user_id)

    def get_all(self):
        return self.repository.get_all()

    def get_pending(self):
        return self.repository.get_pending()

    def register(self, data):
        if not isinstance(data, dict):
            raise ValueError(Messages.REQUEST_DATA_MUST_BE_JSON_OBJECT)

        self.validator.validate_register(data)

        email = data["email"].strip()

        if self.repository.email_exists(email):
            raise ValueError(Messages.EMAIL_ALREADY_EXISTS.format(email))

        return self.repository.create(data)

    def login(self, data):
        if not isinstance(data, dict):
            raise ValueError(Messages.REQUEST_DATA_MUST_BE_JSON_OBJECT)

        self.validator.validate_login(data)

        user = authenticate(
            username = data["email"].strip(),
            password = data["password"],
        )

        if user is None:
            raise ValueError(Messages.INVALID_EMAIL_OR_PASSWORD)

        if user.status == "pending":
            raise ValueError(Messages.ACCOUNT_PENDING_APPROVAL)

        if user.status == "rejected":
            raise ValueError(Messages.REGISTRATION_REJECTED)

        refresh = RefreshToken.for_user(user)

        return {
            "user": user,
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }

    def approve(self, user_id):
        user = self.repository.get(user_id)
        return self.repository.approve(user)

    def reject(self, user_id):
        user = self.repository.get(user_id)
        return self.repository.reject(user)

    def logout(self, refresh_token):
        token = RefreshToken(refresh_token)
        token.blacklist()