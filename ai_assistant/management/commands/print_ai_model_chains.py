"""
Development-only diagnostic: prints the resolved Gemini model fallback chain
for both AI capabilities, exactly as built from current settings, so a
misconfiguration (e.g. empty GEMINI_FALLBACK_MODELS) is visible before any
real Gemini request is made. Never prints GEMINI_API_KEY. manage.py only.

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
