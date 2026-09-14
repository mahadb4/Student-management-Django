# One-off backfill: TeacherService/StudentService.confirm_profile_picture_upload
# now runs every NEW upload through generate_avatar_thumbnail() (see
# common/services/image_service.py), but that only affects uploads made after
# that fix shipped - anyone who uploaded a photo before it still has the
# original, full-resolution file in S3, which is what produces the blurry
# small-avatar look. This command re-processes every EXISTING profile picture
# in place (same S3 key, same DB row - profile_picture_key never changes),
# so nobody has to manually re-upload their photo.
from django.core.management.base import BaseCommand
from common.services.image_service import ImageProcessingError, generate_avatar_thumbnail
from common.services.s3_service import S3Service


class Command(BaseCommand):
    help = "Regenerate square thumbnails for every existing Teacher/Student profile picture already in S3."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action = "store_true",
            help = "List what would be processed without touching S3.",
        )

    def handle(self, *args, **options):
        from students.models import Student
        from teachers.models import Teacher

        dry_run = options["dry_run"]
        s3_service = S3Service()

        processed = 0
        skipped = 0

        for label, queryset in (
            ("teacher", Teacher.objects.select_related("user").exclude(user__profile_picture_key__isnull = True).exclude(user__profile_picture_key = "")),
            ("student", Student.objects.select_related("user").exclude(user__profile_picture_key__isnull = True).exclude(user__profile_picture_key = "")),
        ):
            for obj in queryset:
                key = obj.user.profile_picture_key

                metadata = s3_service.head_object(key)
                if metadata is None:
                    self.stdout.write(self.style.WARNING(f"[{label} {obj.id}] {key} - object not found in S3, skipping."))
                    skipped += 1
                    continue

                if dry_run:
                    self.stdout.write(f"[{label} {obj.id}] {key} - would regenerate.")
                    processed += 1
                    continue

                try:
                    image_bytes = s3_service.get_object_bytes(key)
                    thumbnail_bytes, content_type = generate_avatar_thumbnail(image_bytes, metadata.get("content_type"))
                    s3_service.put_object_bytes(key, thumbnail_bytes, content_type)
                except ImageProcessingError as e:
                    self.stdout.write(self.style.WARNING(f"[{label} {obj.id}] {key} - {e}, skipping."))
                    skipped += 1
                    continue

                self.stdout.write(self.style.SUCCESS(f"[{label} {obj.id}] {key} - regenerated."))
                processed += 1

        verb = "Would regenerate" if dry_run else "Regenerated"
        self.stdout.write(self.style.SUCCESS(f"{verb} {processed} thumbnail(s), skipped {skipped}."))
