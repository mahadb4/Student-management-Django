from io import BytesIO
from PIL import Image, UnidentifiedImageError
from common.constants import PROFILE_PICTURE_THUMBNAIL_SIZE


class ImageProcessingError(ValueError):
    pass


# Center-crop to a square, then downscale to PROFILE_PICTURE_THUMBNAIL_SIZE.
# Called once at upload time (see TeacherService/StudentService
# confirm_profile_picture_upload) so every later read just serves this small,
# already-square file - the blur previously seen in 30-40px avatar circles
# came from browsers downscaling a full-resolution upload directly to that
# size; shrinking server-side once avoids repeating that on every request.
def generate_avatar_thumbnail(image_bytes, content_type, size = PROFILE_PICTURE_THUMBNAIL_SIZE):
    try:
        image = Image.open(BytesIO(image_bytes))
        image.load()
    except UnidentifiedImageError:
        raise ImageProcessingError("The uploaded file is not a valid image.")

    # PNG/WEBP can carry transparency - preserved via RGBA. Anything else
    # (JPEG has none) is flattened to RGB, since JPEG output can't hold alpha.
    has_alpha = image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info)
    image = image.convert("RGBA" if has_alpha else "RGB")

    width, height = image.size
    side = min(width, height)
    left = (width - side) // 2
    top = (height - side) // 2
    image = image.crop((left, top, left + side, top + side))
    image = image.resize((size, size), Image.LANCZOS)

    buffer = BytesIO()
    if content_type == "image/png" or has_alpha:
        image.save(buffer, format = "PNG", optimize = True)
        output_content_type = "image/png"
    else:
        image.save(buffer, format = "JPEG", quality = 88, optimize = True)
        output_content_type = "image/jpeg"

    return buffer.getvalue(), output_content_type
