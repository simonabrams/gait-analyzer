"""
Cloudflare R2 upload/download and presigned URL generation (S3-compatible API).
"""
import os
from pathlib import Path

import boto3
from botocore.config import Config

R2_ACCOUNT_ID = os.environ.get("R2_ACCOUNT_ID", "")
R2_ACCESS_KEY_ID = os.environ.get("R2_ACCESS_KEY_ID", "")
R2_SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY", "")
R2_BUCKET_NAME = os.environ.get("R2_BUCKET_NAME", "gait-analyzer")

_endpoint = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com" if R2_ACCOUNT_ID else None


def _client():
    if not R2_ACCESS_KEY_ID or not R2_SECRET_ACCESS_KEY:
        return None
    return boto3.client(
        "s3",
        endpoint_url=_endpoint,
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        region_name="auto",
        config=Config(signature_version="s3v4"),
    )


def upload_file(local_path: str | Path, r2_key: str) -> None:
    client = _client()
    if not client:
        raise RuntimeError("R2 credentials not configured")
    client.upload_file(str(local_path), R2_BUCKET_NAME, r2_key)


def download_file(r2_key: str, local_path: str | Path) -> None:
    client = _client()
    if not client:
        raise RuntimeError("R2 credentials not configured")
    Path(local_path).parent.mkdir(parents=True, exist_ok=True)
    client.download_file(R2_BUCKET_NAME, r2_key, str(local_path))


def generate_presigned_url(r2_key: str, expiration: int = 3600) -> str:
    client = _client()
    if not client:
        raise RuntimeError("R2 credentials not configured")
    url = client.generate_presigned_url(
        "get_object",
        Params={"Bucket": R2_BUCKET_NAME, "Key": r2_key},
        ExpiresIn=expiration,
    )
    return url


def delete_object(r2_key: str) -> None:
    client = _client()
    if not client:
        return
    try:
        client.delete_object(Bucket=R2_BUCKET_NAME, Key=r2_key)
    except Exception:
        pass


def raw_video_key(run_id: str) -> str:
    return f"raw/{run_id}/input.mp4"


def annotated_video_key(run_id: str) -> str:
    return f"processed/{run_id}/annotated.mp4"


def dashboard_image_key(run_id: str) -> str:
    return f"processed/{run_id}/dashboard.png"
