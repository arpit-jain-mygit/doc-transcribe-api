import logging
import os
import datetime
from google.cloud import storage

logger = logging.getLogger(__name__)

_client = None


def get_gcs_client() -> storage.Client:
    global _client
    if _client is None:
        _client = storage.Client()
    return _client


def get_input_bucket() -> str:
    bucket = os.getenv("INPUT_BUCKET")
    if not bucket:
        raise RuntimeError("INPUT_BUCKET env var is not set")
    return bucket


def upload_file_to_gcs(file_obj, object_name: str) -> str:
    bucket_name = get_input_bucket()
    client = get_gcs_client()

    logger.info(f"GCS upload started: bucket={bucket_name}, object={object_name}")

    bucket = client.bucket(bucket_name)
    blob = bucket.blob(object_name)
    blob.upload_from_file(file_obj)

    gcs_uri = f"gs://{bucket_name}/{object_name}"
    logger.info(f"GCS upload completed: gcs_uri={gcs_uri}")

    return gcs_uri


def generate_signed_url(
    bucket_name: str,
    blob_path: str,
    expiration_minutes: int = 60,
) -> str:
    client = get_gcs_client()

    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)

    url = blob.generate_signed_url(
        version="v4",
        expiration=datetime.timedelta(minutes=expiration_minutes),
        method="GET",
    )

    return url
