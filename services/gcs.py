from google.cloud import storage
import logging
import os
from google.cloud import storage
import datetime

logger = logging.getLogger(__name__)

client = storage.Client()
BUCKET = os.environ["INPUT_BUCKET"]

def upload_file_to_gcs(file_obj, object_name: str) -> str:
    logger.info(f"GCS upload started: object={object_name}")

    bucket = client.bucket(BUCKET)
    blob = bucket.blob(object_name)
    blob.upload_from_file(file_obj)

    gcs_uri = f"gs://{BUCKET}/{object_name}"
    logger.info(f"GCS upload completed: gcs_uri={gcs_uri}")

    return gcs_uri



client = storage.Client()

def generate_signed_url(
    bucket_name: str,
    blob_path: str,
    expiration_minutes: int = 60,
) -> str:
    """
    Generate a signed URL for downloading an object.
    """
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)

    url = blob.generate_signed_url(
        version="v4",
        expiration=datetime.timedelta(minutes=expiration_minutes),
        method="GET",
    )

    return url
