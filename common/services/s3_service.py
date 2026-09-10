import boto3
from botocore.exceptions import ClientError
from django.conf import settings


# Thin wrapper around boto3's S3 client. Knows nothing about students, teachers,
# users, JWT, permissions, enrollment, Django request objects, models or cache -
# just object keys, content types and presigned URLs. All business/authorization
# logic (which key to use, who may request it) lives in the calling service.
class S3Service:
    def __init__(self, bucket_name = None, region_name = None, client = None):
        self.bucket_name = bucket_name or settings.AWS_STORAGE_BUCKET_NAME
        self.region_name = region_name or settings.AWS_S3_REGION_NAME

        self.client = client or boto3.client(
            "s3",
            region_name = self.region_name,
            aws_access_key_id = settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key = settings.AWS_SECRET_ACCESS_KEY,
        )

    # Short-lived presigned PUT URL, scoped to one exact key and content type.
    def generate_upload_url(self, key, content_type, expires_in = 300):
        return self.client.generate_presigned_url(
            "put_object",
            Params = {
                "Bucket": self.bucket_name,
                "Key": key,
                "ContentType": content_type,
            },
            ExpiresIn = expires_in,
        )

    # Short-lived presigned GET URL. Generated fresh on every call - never persisted.
    def generate_view_url(self, key, expires_in = 300):
        return self.client.generate_presigned_url(
            "get_object",
            Params = {
                "Bucket": self.bucket_name,
                "Key": key,
            },
            ExpiresIn = expires_in,
        )

    def object_exists(self, key):
        return self.head_object(key) is not None

    # Returns {"content_length": int, "content_type": str} for an existing object,
    # or None if it doesn't exist. Lets callers verify size/type after upload
    # without trusting whatever the client claims.
    def head_object(self, key):
        try:
            response = self.client.head_object(Bucket = self.bucket_name, Key = key)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code in ("404", "NoSuchKey"):
                return None
            raise

        return {
            "content_length": response.get("ContentLength"),
            "content_type": response.get("ContentType"),
        }

    # Deleting a key that doesn't exist is not an error (S3 delete is idempotent).
    def delete_object(self, key):
        self.client.delete_object(Bucket = self.bucket_name, Key = key)
