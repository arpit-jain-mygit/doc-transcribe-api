# services/gcs.py
# -*- coding: utf-8 -*-

import os
import json
import base64
from datetime import timedelta
from google.cloud import storage

_client = None


def _get_client():
    """
    Create a GCS client using base64-encoded service account JSON
    from GOOGLE_APPLICATION_CREDENTIALS_JSON (Render-safe).
    """
    global _client
    if _client is not None:
        return _client

    creds_b64 = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")

    if not creds_b64:
        raise RuntimeError(
            "GOOGLE_APPLICATION_CREDENTIALS_JSON env var not set in API service"
        )

    creds = json.loads(base64.b64decode(creds_b64))
    _client = storage.Client.from_service_account_info(creds)

    return _client


def generate_signed_url(gcs_uri: str, expires_minutes: int = 15) -> str:
    if not gcs_uri.startswith("gs://"):
        raise ValueError("Invalid GCS URI")

    _, rest = gcs_uri.split("gs://", 1)
    bucket_name, blob_name = rest.split("/", 1)

    filename = blob_name.split("/")[-1]

    client = _get_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)

    return blob.generate_signed_url(
        version="v4",
        expiration=timedelta(minutes=expires_minutes),
        method="GET",
        response_disposition=f'attachment; filename="{filename}"',
        response_type="text/plain",
    )

