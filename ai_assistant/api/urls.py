from django.urls import path
from .ask_api import ask_api

urlpatterns = [
    path("ai-assistant/ask/", ask_api, name="ai_assistant_ask"),
]
