import io
import json

import storage
from conftest import FakeClientError


class FakeS3:
    def __init__(self):
        self.objects = {}
        self.presigned_calls = []

    def get_object(self, Bucket, Key):
        if Key not in self.objects:
            raise FakeClientError("NoSuchKey")
        return {"Body": io.BytesIO(self.objects[Key]["Body"])}

    def put_object(self, Bucket, Key, Body, ContentType):
        self.objects[Key] = {"Bucket": Bucket, "Body": Body, "ContentType": ContentType}

    def generate_presigned_url(self, operation, Params, ExpiresIn):
        self.presigned_calls.append((operation, Params, ExpiresIn))
        return f"https://signed.test/{Params['Key']}"


def test_metadata_crud_uses_expected_s3_key(monkeypatch):
    fake = FakeS3()
    monkeypatch.setattr(storage, "s3", fake)

    storage.save_metadata("session-1", {"sessionId": "session-1"})
    result = storage.load_metadata("session-1")

    assert result == {"sessionId": "session-1"}
    saved = fake.objects["sessions/session-1/metadata.json"]
    assert saved["ContentType"] == "application/json"
    assert json.loads(saved["Body"].decode()) == {"sessionId": "session-1"}


def test_adventure_crud_returns_none_for_missing_key(monkeypatch):
    fake = FakeS3()
    monkeypatch.setattr(storage, "s3", fake)

    assert storage.load_adventure("session-1", "game-1") is None

    storage.save_adventure("session-1", "game-1", {"gameId": "game-1"})

    assert storage.load_adventure("session-1", "game-1") == {"gameId": "game-1"}


def test_binary_write_and_presigned_url(monkeypatch):
    fake = FakeS3()
    monkeypatch.setattr(storage, "s3", fake)

    storage.write_binary("images/turn.png", b"png", "image/png")
    url = storage.presigned_url("images/turn.png", expires_in=99)

    assert fake.objects["images/turn.png"]["Body"] == b"png"
    assert fake.objects["images/turn.png"]["ContentType"] == "image/png"
    assert url == "https://signed.test/images/turn.png"
    assert fake.presigned_calls == [
        ("get_object", {"Bucket": "test-bucket", "Key": "images/turn.png"}, 99)
    ]
