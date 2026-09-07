from users.dtos.user_list_dto import UserListDTO
from users.dtos.user_detail_dto import UserDetailDTO


class UserMapper:
    # Used by the Admin-facing /users/ and /users/pending/ lists - callers
    # only need enough to identify and act on a row (approve/reject/view),
    # not the full permissions/profile-linkage detail.
    @staticmethod
    def to_list_dto(user):
        return UserListDTO(
            id = user.id,
            name = user.name,
            email = user.email,
            role = user.role,
            status = user.status,
        ).to_dict()

    # Used wherever the caller needs the full identity: single-user GET,
    # register/login/approve/reject responses, and the authenticated
    # /me/ and onboarding endpoints (which also need student_id/teacher_id
    # to know whether a profile is already linked).
    @staticmethod
    def to_detail_dto(user):
        student = getattr(user, "student_profile", None)
        teacher = getattr(user, "teacher_profile", None)

        return UserDetailDTO(
            id = user.id,
            name = user.name,
            email = user.email,
            role = user.role,
            status = user.status,
            permissions = [],
            student_id = student.id if student else None,
            teacher_id = teacher.id if teacher else None,
        ).to_dict()
