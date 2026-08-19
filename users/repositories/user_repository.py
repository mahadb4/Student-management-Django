from common.repositories.base_repository import BaseRepository
from users.models import User


class UserRepository(BaseRepository):
    def __init__(self):
        super().__init__(User)

    def email_exists(self, email, exclude_id = None):
        query = self.model.objects.filter(email__iexact = email)

        if exclude_id is not None:
            query = query.exclude(id = exclude_id)

        return query.exists()

    def get_by_email(self, email):
        return self.model.objects.get(email__iexact = email)

    def get_pending(self):
        return self.model.objects.filter(status = "pending")

    def create(self, data):
        return self.model.objects.create_user(
            email = data["email"].strip(),
            name = data["name"].strip(),
            password = data["password"],
            role = data["role"],
            status = "pending",
        )

    def approve(self, user):
        user.status = "approved"
        user.save()
        return user

    def reject(self, user):
        user.status = "rejected"
        user.save()
        return user