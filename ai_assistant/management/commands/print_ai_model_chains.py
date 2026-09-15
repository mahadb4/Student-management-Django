"""
Development-only diagnostic: prints the resolved Gemini model fallback
chain for both AI capabilities (Student Assistant and Assignment
Evaluation), exactly as GeminiGenerationService/AssignmentEvaluationService
would build it from current settings - so a misconfiguration (e.g. an
empty GEMINI_FALLBACK_MODELS, as diagnosed on 2026-09-15: the .env file
never defined it at all, so the assistant silently ran with a 1-model
chain and had nowhere to fall back to on a NOT_FOUND) is visible with one
command, before any real Gemini request is made.

Never prints GEMINI_API_KEY or any other secret. Not wired into any URL/
API - `manage.py` only.

Usage:
    python manage.py print_ai_model_chains
"""
from django.conf import settings
from django.core.management.base import BaseCommand

from common.ai.model_router import build_model_chain


class Command(BaseCommand):
    help = "Prints the resolved Gemini model fallback chain for each AI capability, from current settings."

    def handle(self, *args, **options):
        assistant_chain = build_model_chain(settings.GEMINI_PRIMARY_MODEL, settings.GEMINI_FALLBACK_MODELS)
        assignment_chain = build_model_chain(
            settings.GEMINI_ASSIGNMENT_PRIMARY_MODEL, settings.GEMINI_ASSIGNMENT_FALLBACK_MODELS
        )

        self.stdout.write("Student AI Assistant model chain (ai_assistant.services.gemini_generation_service):")
        self._print_chain(assistant_chain)

        self.stdout.write("")
        self.stdout.write("Assignment Evaluation model chain (assignments.services.assignment_evaluation_service):")
        self._print_chain(assignment_chain)

        if len(assistant_chain) == 1:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING(
                "Student AI Assistant has only ONE model configured - GEMINI_FALLBACK_MODELS "
                "is unset/empty, so a single model failure has nowhere to fall back to."
            ))

    def _print_chain(self, chain):
        self.stdout.write("  [")
        for name in chain:
            self.stdout.write(f'      "{name}",')
        self.stdout.write("  ]")
