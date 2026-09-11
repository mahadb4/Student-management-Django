from django.urls import path
from .remark_api import remark_api

urlpatterns = [
    path("remarks/", remark_api, name = "remark_api_list"),
    path("remarks/<int:remark_id>/", remark_api, name = "remark_api_detail"),
]
