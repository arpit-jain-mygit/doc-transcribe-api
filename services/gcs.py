# services/gcs.py

from google.cloud import storage
from datetime import timedelta


def generate_signed_url(gcs_uri: str, expires_minutes: int = 15) -> str:
    """
    Generate a temporary HTTPS download URL for a GCS object.

    API service account requires:
      roles/storage.objectViewer
    """
    if not gcs_uri.startswith("gs://"):
        raise ValueError("Invalid GCS URI")

    _, rest = gcs_uri.split("gs://", 1)
    bucket_name, blob_name = rest.split("/", 1)

    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)

    return blob.generate_signed_url(
        version="v4",
        expiration=timedelta(minutes=expires_minutes),
        method="GET",
    )
