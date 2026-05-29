import json
import os
import boto3
from botocore.exceptions import ClientError

s3 = boto3.client('s3')

def _must_env(var):
    v = os.environ.get(var)
    if not v:
        raise RuntimeError(f"Required environment variable '{var}' is not set")
    return v

def _bucket():
    return _must_env('S3_BUCKET_NAME')

def _read_json(key: str):
    try:
        obj = s3.get_object(Bucket=_bucket(), Key=key)
        return json.loads(obj['Body'].read().decode())
    except ClientError as e:
        if e.response['Error']['Code'] in ('NoSuchKey', '404'):
            return None
        print(f"[storage.py] S3 ClientError for {key}: {e}")
        raise
    except Exception as e:
        print(f"[storage.py] Network or unknown error during read {key}: {e}")
        return None

def _write_json(key: str, data: dict):
    try:
        s3.put_object(Bucket=_bucket(), Key=key, Body=json.dumps(data).encode(), ContentType='application/json')
    except Exception as e:
        print(f"[storage.py] S3 write failed for {key}: {e}")
        raise


def write_binary(key: str, data: bytes, content_type: str):
    try:
        s3.put_object(Bucket=_bucket(), Key=key, Body=data, ContentType=content_type)
    except Exception as e:
        print(f"[storage.py] S3 binary write failed for {key}: {e}")
        raise


def presigned_url(key: str, expires_in: int = 3600):
    if not key:
        return ""
    try:
        return s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": _bucket(), "Key": key},
            ExpiresIn=expires_in,
        )
    except Exception as e:
        print(f"[storage.py] S3 presigned URL failed for {key}: {e}")
        return ""

def load_metadata(session_id: str):
    return _read_json(f"sessions/{session_id}/metadata.json")

def save_metadata(session_id: str, data: dict):
    _write_json(f"sessions/{session_id}/metadata.json", data)

def load_adventure(session_id: str, game_id: str):
    return _read_json(f"sessions/{session_id}/adventures/{game_id}.json")

def save_adventure(session_id: str, game_id: str, data: dict):
    _write_json(f"sessions/{session_id}/adventures/{game_id}.json", data)
