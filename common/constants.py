HTTP_OK = 200
HTTP_CREATED = 201
HTTP_BAD_REQUEST = 400
HTTP_NOT_FOUND = 404
HTTP_METHOD_NOT_ALLOWED = 405
HTTP_SERVER_ERROR = 500

# ── Profile pictures (S3) ────────────────────────────────────────────────────
# Maps an accepted upload Content-Type to the file extension used in the S3 key.
PROFILE_PICTURE_CONTENT_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}
MAX_PROFILE_PICTURE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
PROFILE_PICTURE_URL_EXPIRY_SECONDS = 300  # 5 minutes, for both upload and view URLs
# Every consumer (admin Students/Teachers lists, Attendance register, "My
# Courses" teacher avatar, the uploader's own preview) renders this at well
# under 40px - a square this size still looks sharp there, and downscaling
# from it (instead of from a multi-megapixel original) is what avoids the
# blurry-avatar look a browser produces scaling a huge source image straight
# down to a tiny circle.
PROFILE_PICTURE_THUMBNAIL_SIZE = 256

# ── Assignment attachments / submissions (S3) ───────────────────────────────
# Same key-by-Content-Type approach as PROFILE_PICTURE_CONTENT_TYPES.
ASSIGNMENT_FILE_CONTENT_TYPES = {
    "application/pdf": "pdf",
    "application/msword": "doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/zip": "zip",
    "application/x-zip-compressed": "zip",
}
MAX_ASSIGNMENT_FILE_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB
ASSIGNMENT_FILE_URL_EXPIRY_SECONDS = 300  # 5 minutes, for both upload and view URLs