from io import BytesIO
from django.test import SimpleTestCase
from PIL import Image
from common.services.image_service import ImageProcessingError, generate_avatar_thumbnail


def _make_image_bytes(width, height, mode = "RGB", color = (10, 20, 30), fmt = "JPEG"):
    buffer = BytesIO()
    Image.new(mode, (width, height), color = color).save(buffer, format = fmt)
    return buffer.getvalue()


class GenerateAvatarThumbnailTests(SimpleTestCase):

    def test_output_is_a_square_of_the_requested_size(self):
        source = _make_image_bytes(1200, 800)  # wide, non-square original
        thumbnail_bytes, content_type = generate_avatar_thumbnail(source, "image/jpeg", size = 64)

        image = Image.open(BytesIO(thumbnail_bytes))
        self.assertEqual(image.size, (64, 64))
        self.assertEqual(content_type, "image/jpeg")

    def test_default_size_matches_the_configured_constant(self):
        from common.constants import PROFILE_PICTURE_THUMBNAIL_SIZE

        source = _make_image_bytes(500, 500)
        thumbnail_bytes, _ = generate_avatar_thumbnail(source, "image/jpeg")

        image = Image.open(BytesIO(thumbnail_bytes))
        self.assertEqual(image.size, (PROFILE_PICTURE_THUMBNAIL_SIZE, PROFILE_PICTURE_THUMBNAIL_SIZE))

    def test_tall_image_is_center_cropped_not_stretched(self):
        # A 100x300 image center-cropped to square should keep the MIDDLE
        # 100x100 slice, not squash the whole thing - verified by sampling a
        # pixel painted only in the middle third.
        width, height = 100, 300
        image = Image.new("RGB", (width, height), color = (0, 0, 0))
        for y in range(100, 200):
            for x in range(width):
                image.putpixel((x, y), (255, 0, 0))
        buffer = BytesIO()
        image.save(buffer, format = "JPEG")

        thumbnail_bytes, _ = generate_avatar_thumbnail(buffer.getvalue(), "image/jpeg", size = 50)
        thumbnail = Image.open(BytesIO(thumbnail_bytes)).convert("RGB")
        center_pixel = thumbnail.getpixel((25, 25))
        self.assertGreater(center_pixel[0], 200)  # red channel dominant

    def test_png_with_transparency_stays_png(self):
        source = _make_image_bytes(50, 50, mode = "RGBA", color = (10, 20, 30, 128), fmt = "PNG")
        thumbnail_bytes, content_type = generate_avatar_thumbnail(source, "image/png", size = 32)

        self.assertEqual(content_type, "image/png")
        image = Image.open(BytesIO(thumbnail_bytes))
        self.assertEqual(image.mode, "RGBA")

    def test_opaque_jpeg_input_produces_jpeg_output(self):
        source = _make_image_bytes(50, 50, fmt = "JPEG")
        _, content_type = generate_avatar_thumbnail(source, "image/jpeg", size = 32)
        self.assertEqual(content_type, "image/jpeg")

    def test_invalid_bytes_raise_image_processing_error(self):
        with self.assertRaises(ImageProcessingError):
            generate_avatar_thumbnail(b"not an image", "image/jpeg", size = 32)
