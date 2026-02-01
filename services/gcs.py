# -*- coding: utf-8 -*-

import os
import json
import base64
import datetime
from google.cloud import storage

# =========================================================
# LAZY CLIENT
# =========================================================
_client = None


def _get_client():
    global _client
    if _client is not None:
        return _client

    creds_b64 = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    if creds_b64:
        creds = json.loads(base64.b64decode(creds_b64))
        _client = storage.Client.from_service_account_info(creds)
    else:
        _client = storage.Client()

    return _client


# =========================================================
# UPLOAD FILE (STREAM SAFE)
# =========================================================
def upload_file(
    *,
    file_obj,
    destination_path: str,
) -> dict:
    bucket_name = os.getenv("GCS_BUCKET_NAME")
    if not bucket_name:
        raise RuntimeError("GCS_BUCKET_NAME not set")

    client = _get_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(destination_path)

    # IMPORTANT: stream upload (UploadFile.file)
    blob.upload_from_file(file_obj)

    return {
        "bucket": bucket_name,
        "blob": destination_path,
        "gcs_uri": f"gs://{bucket_name}/{destination_path}",
    }


# =========================================================
# UPLOAD TEXT
# =========================================================
def upload_text(
    *,
    content: str,
    destination_path: str,
) -> dict:
    bucket_name = os.getenv("GCS_BUCKET_NAME")
    if not bucket_name:
        raise RuntimeError("GCS_BUCKET_NAME not set")

    client = _get_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(destination_path)

    blob.upload_from_string(
        content,
        content_type="text/plain; charset=utf-8",
    )

    return {
        "bucket": bucket_name,
        "blob": destination_path,
        "gcs_uri": f"gs://{bucket_name}/{destination_path}",
    }


# =========================================================
# SIGNED URL (USED BY status.py)
# =========================================================
def generate_signed_url(
    *,
    bucket_name: str,
    blob_path: str,
    expires_days: int = 1,
) -> str:
    """
    Generate browser-downloadable HTTPS URL.
    """
    client = _get_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)

    return blob.generate_signed_url(
        version="v4",
        expiration=datetime.timedelta(days=expires_days),
        method="GET",
    )


# =========================================================
# DOWNLOAD FROM GCS (WORKER)
# =========================================================
def download_from_gcs(gcs_uri: str) -> str:
    """
    Download a GCS object to /tmp and return local path.
    """
    if not gcs_uri.startswith("gs://"):
        raise ValueError(f"Invalid GCS URI: {gcs_uri}")

    client = _get_client()

    path = gcs_uri.replace("gs://", "")
    bucket_name, blob_path = path.split("/", 1)

    local_path = f"/tmp/{os.path.basename(blob_path)}"

    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)
    blob.download_to_filename(local_path)

    return local_path
