from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .user_api import (
    user_api,
    register_api,
    login_api,
    logout_api,
    approve_user_api,
    reject_user_api,
    pending_users_api,
    me_api,
    complete_onboarding_api,
)


urlpatterns = [
    path("", user_api, name="user_api"),
    path("<int:user_id>/", user_api, name="user_detail_api"),

    path("register/", register_api, name="register_api"),
    path("login/", login_api, name="login_api"),
    path("refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("logout/", logout_api, name="logout_api"),
    path("me/", me_api, name="me_api"),
    path("onboarding/", complete_onboarding_api, name="complete_onboarding_api"),
    path("pending/", pending_users_api, name="pending_users_api"),

    path("<int:user_id>/approve/", approve_user_api, name="approve_user_api"),
    path("<int:user_id>/reject/", reject_user_api, name="reject_user_api"),
]