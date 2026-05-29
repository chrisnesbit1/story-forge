import io
import os
import sys
import types
from pathlib import Path

os.environ.setdefault("S3_BUCKET_NAME", "test-bucket")
os.environ.setdefault("GEMINI_API_KEY", "test-key")

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))


class FakeClientError(Exception):
    def __init__(self, code: str):
        self.response = {"Error": {"Code": code}}
        super().__init__(code)


class EmptyS3Client:
    def get_object(self, **kwargs):
        raise FakeClientError("NoSuchKey")

    def put_object(self, **kwargs):
        return {}

    def generate_presigned_url(self, *args, **kwargs):
        return "https://example.test/signed"


if "boto3" not in sys.modules:
    boto3 = types.ModuleType("boto3")
    boto3.client = lambda service_name: EmptyS3Client()
    sys.modules["boto3"] = boto3

if "botocore" not in sys.modules:
    botocore = types.ModuleType("botocore")
    exceptions = types.ModuleType("botocore.exceptions")
    exceptions.ClientError = FakeClientError
    botocore.exceptions = exceptions
    sys.modules["botocore"] = botocore
    sys.modules["botocore.exceptions"] = exceptions
