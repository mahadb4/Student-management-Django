from django.test import TestCase
from botocore.exceptions import ClientError
from common.services.s3_service import S3Service


#Hand-written fake of the tiny slice of the boto3 S3 client S3Service uses,
#matching this repo's existing stub/fake convention (no real AWS calls, no moto).
class FakeBotoClient:

    def __init__(self):
        self.objects = {}  # key -> {"ContentLength": int, "ContentType": str}
        self.presign_calls = []

    def generate_presigned_url(self, operation, Params, ExpiresIn):
        self.presign_calls.append((operation, Params, ExpiresIn))
        return f"https://fake-s3/{Params['Bucket']}/{Params['Key']}?op={operation}&expires={ExpiresIn}"

    def head_object(self, Bucket, Key):
        if Key not in self.objects:
            raise ClientError({"Error": {"Code": "404", "Message": "Not Found"}}, "HeadObject")
        return self.objects[Key]

    def delete_object(self, Bucket, Key):
        self.objects.pop(Key, None)


class S3ServiceTests(TestCase):

    def setUp(self):
        self.client = FakeBotoClient()
        self.service = S3Service(bucket_name = "test-bucket", region_name = "us-east-1", client = self.client)

    def test_generate_upload_url_signs_put_with_exact_key_and_content_type(self):
        url = self.service.generate_upload_url("students/1/profile.jpg", "image/jpeg", expires_in = 300)

        operation, params, expires_in = self.client.presign_calls[0]
        self.assertEqual(operation, "put_object")
        self.assertEqual(params["Bucket"], "test-bucket")
        self.assertEqual(params["Key"], "students/1/profile.jpg")
        self.assertEqual(params["ContentType"], "image/jpeg")
        self.assertEqual(expires_in, 300)
        self.assertIn("students/1/profile.jpg", url)

    def test_generate_view_url_signs_get(self):
        self.service.generate_view_url("teachers/2/profile.png", expires_in = 300)

        operation, params, expires_in = self.client.presign_calls[0]
        self.assertEqual(operation, "get_object")
        self.assertEqual(params["Key"], "teachers/2/profile.png")
        self.assertEqual(expires_in, 300)

    def test_object_exists_true_when_head_object_succeeds(self):
        self.client.objects["students/1/profile.jpg"] = {"ContentLength": 100, "ContentType": "image/jpeg"}
        self.assertTrue(self.service.object_exists("students/1/profile.jpg"))

    def test_object_exists_false_when_missing(self):
        self.assertFalse(self.service.object_exists("students/1/profile.jpg"))

    def test_head_object_returns_metadata(self):
        self.client.objects["students/1/profile.jpg"] = {"ContentLength": 12345, "ContentType": "image/jpeg"}
        metadata = self.service.head_object("students/1/profile.jpg")
        self.assertEqual(metadata, {"content_length": 12345, "content_type": "image/jpeg"})

    def test_head_object_returns_none_when_missing(self):
        self.assertIsNone(self.service.head_object("does/not/exist.jpg"))

    def test_delete_object_removes_it(self):
        self.client.objects["students/1/profile.jpg"] = {"ContentLength": 1, "ContentType": "image/jpeg"}
        self.service.delete_object("students/1/profile.jpg")
        self.assertNotIn("students/1/profile.jpg", self.client.objects)

    def test_delete_object_on_missing_key_does_not_raise(self):
        self.service.delete_object("never/existed.jpg")
