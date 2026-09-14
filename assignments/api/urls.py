from django.urls import path
from .assignment_api import assignment_api, assignment_attachment_upload_url_api, assignment_attachment_confirm_api
from .submission_api import my_submission_api, submission_upload_url_api, submission_confirm_api, assignment_submissions_api
from .ai_evaluation_api import assignment_ai_check_api, assignment_evaluation_review_api

urlpatterns = [
    path("assignments/", assignment_api, name = "assignment_api_list"),
    path("assignments/<int:assignment_id>/", assignment_api, name = "assignment_api_detail"),
    path("assignments/<int:assignment_id>/attachment-upload-url/", assignment_attachment_upload_url_api, name = "assignment_attachment_upload_url"),
    path("assignments/<int:assignment_id>/attachment-confirm/", assignment_attachment_confirm_api, name = "assignment_attachment_confirm"),
    path("assignments/<int:assignment_id>/submission/", my_submission_api, name = "my_submission"),
    path("assignments/<int:assignment_id>/submission/upload-url/", submission_upload_url_api, name = "submission_upload_url"),
    path("assignments/<int:assignment_id>/submission/confirm/", submission_confirm_api, name = "submission_confirm"),
    path("assignments/<int:assignment_id>/submissions/", assignment_submissions_api, name = "assignment_submissions"),
    path("assignments/<int:assignment_id>/submissions/<int:student_id>/ai-check/", assignment_ai_check_api, name = "assignment_ai_check"),
    path("assignments/<int:assignment_id>/submissions/<int:student_id>/evaluation/", assignment_evaluation_review_api, name = "assignment_evaluation_review"),
]
