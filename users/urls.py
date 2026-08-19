from django.urls import path
from users import views


urlpatterns = [
    path("register/", views.register_api),
    path("login/", views.login_api),
    path("logout/", views.logout_api),
    path("me/", views.me_api),
    path("", views.user_api),
    path("pending/", views.pending_users_api),
    path("<int:user_id>/", views.user_api),
    path("<int:user_id>/approve/", views.approve_user_api),
    path("<int:user_id>/reject/", views.reject_user_api),
]