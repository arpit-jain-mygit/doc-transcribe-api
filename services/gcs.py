# User value: This file helps users get reliable OCR/transcription results with clear processing behavior.
# -*- coding: utf-8 -*-

import os
import json
import base64
from datetime import timedelta
from google.cloud import storage

_client = None


# User value: This step keeps the user OCR/transcription flow accurate and dependable.
def _get_client():
    global _client
    if _client:
        return _client

    creds_b64 = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    if creds_b64:
        creds = json.loads(base64.b64decode(creds_b64))
        _client = storage.Client.from_service_account_info(creds)
    else:
        _client = storage.Client()

    return _client


# ---------------------------------------------------------
# UPLOAD FILE (stream-safe)
# ---------------------------------------------------------
# User value: This step keeps the user OCR/transcription flow accurate and dependable.
def upload_file(file_obj, destination_path: str) -> dict:
    bucket_name = os.getenv("GCS_BUCKET_NAME")
    if not bucket_name:
        raise RuntimeError("GCS_BUCKET_NAME not set")

    client = _get_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(destination_path)

    blob.upload_from_file(file_obj)

    return {
        "bucket": bucket_name,
        "blob": destination_path,
        "gcs_uri": f"gs://{bucket_name}/{destination_path}",
    }


# ---------------------------------------------------------
# UPLOAD TEXT
# ---------------------------------------------------------
# User value: This step keeps the user OCR/transcription flow accurate and dependable.
def upload_text(*, content: str, destination_path: str) -> dict:
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


# ---------------------------------------------------------
# SIGNED DOWNLOAD URL (STANDARDIZED)
# ---------------------------------------------------------
# User value: This step keeps the user OCR/transcription flow accurate and dependable.
def generate_signed_url(
    *,
    bucket_name: str,
    blob_path: str,
    expiration_minutes: int = 60,
    download_filename: str | None = None,
    response_type: str | None = "text/plain; charset=utf-8",
) -> str:
    client = _get_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)

    return blob.generate_signed_url(
        version="v4",
        expiration=timedelta(minutes=expiration_minutes),
        method="GET",
        response_disposition=(
            f'attachment; filename="{download_filename}"'
            if download_filename
            else None
        ),
        response_type=response_type,
    )
