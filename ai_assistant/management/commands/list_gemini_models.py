"""
Development-only diagnostic: lists the Gemini model names actually
accessible to the configured GEMINI_API_KEY/project via client.models.list()
- the SDK's own model-listing capability, never a generate_content() call
(no generation quota is spent running this command).

Not wired into any URL/API - this is a `manage.py` command only, run
manually by a developer/operator to check whether the models named in
GEMINI_PRIMARY_MODEL/GEMINI_FALLBACK_MODELS (and the GEMINI_ASSIGNMENT_*
equivalents) are actually available before adding them to a fallback
chain. Never exposes anything to the frontend or any authenticated
student/teacher-facing endpoint.

Usage:
    python manage.py list_gemini_models
    python manage.py list_gemini_models --check gemini-2.5-flash,gemini-3.5-flash-lite,gemini-3.8-flash
"""
from django.conf import settings
from django.core.management.base import BaseCommand
from google import genai


class Command(BaseCommand):
    help = (
        "Lists Gemini models accessible to the configured API key via "
        "client.models.list() (no generate_content calls, no quota spent). "
        "Optionally checks specific model names against that list."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--check",
            type=str,
            default=None,
            help="Comma-separated model names to check for availability against the listed models.",
        )

    def handle(self, *args, **options):
        client = genai.Client(api_key=settings.GEMINI_API_KEY)

        available = []
        for model in client.models.list():
            # `model.name` is normally "models/<id>" - normalize to the
            # bare id, matching how GEMINI_PRIMARY_MODEL/GEMINI_FALLBACK_
            # MODELS are configured (e.g. "gemini-2.5-flash").
            name = (model.name or "").split("/")[-1]
            supports_generate_content = bool(
                getattr(model, "supported_actions", None)
                and "generateContent" in model.supported_actions
            )
            available.append((name, supports_generate_content))

        self.stdout.write(f"Models accessible to this API key/project ({len(available)}):")
        for name, supports_generate_content in sorted(available):
            marker = "generateContent" if supports_generate_content else "no generateContent"
            self.stdout.write(f"  - {name} [{marker}]")

        check_arg = options.get("check")
        if not check_arg:
            return

        requested = [m.strip() for m in check_arg.split(",") if m.strip()]
        available_names = {name for name, _ in available}
        generate_content_names = {name for name, supports in available if supports}

        self.stdout.write("")
        self.stdout.write("Availability check:")
        for model_name in requested:
            if model_name in generate_content_names:
                self.stdout.write(self.style.SUCCESS(f"  {model_name}: available (supports generateContent)"))
            elif model_name in available_names:
                self.stdout.write(self.style.WARNING(f"  {model_name}: listed, but does NOT support generateContent"))
            else:
                self.stdout.write(self.style.ERROR(f"  {model_name}: NOT available for this API key/project"))
