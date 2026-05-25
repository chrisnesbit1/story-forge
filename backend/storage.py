import json
import os
import boto3
from botocore.exceptions import ClientError

s3 = boto3.client('s3')


def _bucket():
    return os.environ['S3_BUCKET_NAME']


def _read_json(key: str):
    try:
        obj = s3.get_object(Bucket=_bucket(), Key=key)
        return json.loads(obj['Body'].read().decode())
    except ClientError as e:
        if e.response['Error']['Code'] in ('NoSuchKey', '404'):
            return None
        raise


def _write_json(key: str, data: dict):
    s3.put_object(Bucket=_bucket(), Key=key, Body=json.dumps(data).encode(), ContentType='application/json')


def load_metadata(session_id: str):
    return _read_json(f"sessions/{session_id}/metadata.json")


def save_metadata(session_id: str, data: dict):
    _write_json(f"sessions/{session_id}/metadata.json", data)


def load_adventure(session_id: str, game_id: str):
    return _read_json(f"sessions/{session_id}/adventures/{game_id}.json")


def save_adventure(session_id: str, game_id: str, data: dict):
    _write_json(f"sessions/{session_id}/adventures/{game_id}.json", data)
