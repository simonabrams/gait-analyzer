"""
Cloudflare R2 upload/download and presigned URL generation (S3-compatible API).
When LOCAL_STORAGE_PATH is set and R2 is not configured, uses local disk instead (for dev).
"""
import os
import shutil
from pathlib import Path

import boto3
from botocore.config import Config

R2_ACCOUNT_ID = os.environ.get("R2_ACCOUNT_ID", "")
R2_ACCESS_KEY_ID = os.environ.get("R2_ACCESS_KEY_ID", "")
R2_SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY", "")
R2_BUCKET_NAME = os.environ.get("R2_BUCKET_NAME", "gait-analyzer")
# On Render the filesystem is ephemeral; require R2 and do not use local storage by default.
_LOCAL_DEFAULT = "" if os.environ.get("RENDER") == "true" else ".local_storage"
LOCAL_STORAGE_PATH = os.environ.get("LOCAL_STORAGE_PATH", _LOCAL_DEFAULT)
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000").rstrip("/")

_endpoint = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com" if R2_ACCOUNT_ID else None


def _use_local_storage() -> bool:
    return bool(LOCAL_STORAGE_PATH) and not (R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY)


def _local_path(r2_key: str) -> Path:
    parts = r2_key.split("/")
    return Path(LOCAL_STORAGE_PATH).joinpath(*parts)


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
    if _use_local_storage():
        dest = _local_path(r2_key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(local_path), str(dest))
        return
    client = _client()
    if not client:
        raise RuntimeError("R2 credentials not configured; set LOCAL_STORAGE_PATH for local dev")
    client.upload_file(str(local_path), R2_BUCKET_NAME, r2_key)


def download_file(r2_key: str, local_path: str | Path) -> None:
    if _use_local_storage():
        src = _local_path(r2_key)
        if not src.is_file():
            raise FileNotFoundError(
                f"Video not found at {src}. "
                "On Render/production the filesystem is ephemeral—configure R2 (R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME) and do not set LOCAL_STORAGE_PATH."
            )
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(src), str(local_path))
        return
    client = _client()
    if not client:
        raise RuntimeError("R2 credentials not configured")
    Path(local_path).parent.mkdir(parents=True, exist_ok=True)
    client.download_file(R2_BUCKET_NAME, r2_key, str(local_path))


def generate_presigned_url(r2_key: str, expiration: int = 3600) -> str:
    if _use_local_storage():
        parts = r2_key.split("/")
        if len(parts) >= 3:
            run_id, filename = parts[1], parts[2]
            return f"{API_BASE_URL}/api/local-artifacts/{run_id}/{filename}"
        return ""
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
    if _use_local_storage():
        p = _local_path(r2_key)
        try:
            if p.is_file():
                p.unlink()
        except OSError:
            pass
        return
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
