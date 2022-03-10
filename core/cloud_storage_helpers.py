import logging
from datetime import timedelta

from django.conf import settings
from google.auth import compute_engine
from google.auth.transport import requests
from gcloud.storage import Client, Bucket


log = logging.getLogger(__name__)


class NoSuchBlobException(BaseException):
    pass


def get_signed_url(
    filename,
    bucket_name,
    storage_client: Client = settings.CLOUD_STORAGE_CLIENT,
    expiration: timedelta = settings.SIGNED_STORAGE_URL_EXPIRATION_DELTA,
) -> str:
    """Generates a v4 signed URL for downloading a blob."""

    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(filename)

    signing_credentials = None

    if settings.IN_GCP:  # running in GCP Platform
        auth_request = requests.Request()
        signing_credentials = compute_engine.IDTokenCredentials(auth_request, "")

    url = blob.generate_signed_url(
        version="v4",
        credentials=signing_credentials,
        # This URL is valid for 30 minutes
        expiration=expiration,
        # Allow GET requests using this URL.
        method="GET",
    )
    log.info(f"Generated GET signed URL: {url}")
    return url
