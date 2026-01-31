# -*- coding: utf-8 -*-

import os
import json
import base64
import datetime
from google.cloud import storage

_client = None


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


def generate_signed_url(
    bucket_name: str,
    blob_path: str,
    expiration_minutes: int = 60,
) -> str:
    client = _get_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)

    return blob.generate_signed_url(
        version="v4",
        expiration=datetime.timedelta(minutes=expiration_minutes),
        method="GET",
    )
