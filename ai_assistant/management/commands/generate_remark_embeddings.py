# One-off/repeatable backfill: creates a RemarkEmbedding for every Remark
# that doesn't have one yet (or whose embedded_text has gone stale relative
# to the current remark_text), via the Gemini embedding API. Safe to re-run -
# embed_remark() updates the existing RemarkEmbedding in place rather than
# creating a duplicate, since it's a OneToOneField.
from django.core.management.base import BaseCommand

from ai_assistant.services.gemini_embedding_service import EmbeddingGenerationError, GeminiEmbeddingService
from ai_assistant.services.remark_embedding_service import embed_remark, remark_embedding_is_stale
from remarks.models import Remark


class Command(BaseCommand):
    help = "Generate (or refresh stale) Gemini embeddings for existing Remarks that don't have a current one."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true",
            help="List which remarks would be embedded without calling Gemini or writing to the database.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        embedding_service = GeminiEmbeddingService()

        embedded = 0
        skipped_up_to_date = 0
        failed = 0

        for remark in Remark.objects.select_related("embedding").all():
            if not remark_embedding_is_stale(remark):
                skipped_up_to_date += 1
                continue

            if dry_run:
                self.stdout.write(f"[remark {remark.id}] would embed.")
                embedded += 1
                continue

            try:
                embed_remark(remark, embedding_service=embedding_service)
            except EmbeddingGenerationError as e:
                self.stdout.write(self.style.WARNING(f"[remark {remark.id}] failed: {e}"))
                failed += 1
                continue

            self.stdout.write(self.style.SUCCESS(f"[remark {remark.id}] embedded."))
            embedded += 1

        verb = "Would embed" if dry_run else "Embedded"
        self.stdout.write(self.style.SUCCESS(
            f"{verb} {embedded} remark(s). Already up to date: {skipped_up_to_date}. Failed: {failed}."
        ))
