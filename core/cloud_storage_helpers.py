import logging
from datetime import datetime, timedelta

from django.conf import settings
from google.auth import compute_engine
from google.auth.transport import requests
from gcloud.storage import Client, Bucket


log = logging.getLogger(__name__)

class NoSuchBlobException(BaseException):
    pass


def get_signed_url(
    filename: str,
    bucket_name: str,
    client: Client = settings.CLOUD_STORAGE_CLIENT,
    expiration: timedelta = settings.SIGNED_STORAGE_URL_EXPIRATION_DELTA,
):
    payload = {"expiration": expiration}
    compute_signed_kwargs = {}
    if settings.IN_GCP:
        signing_credentials = None
        auth_request = requests.Request()
        signing_credentials = compute_engine.IDTokenCredentials(auth_request, "")
        compute_signed_kwargs = {"credentials": signing_credentials, "expiration": expiration, "method": "GET"}

    try:
        bucket: Bucket = client.get_bucket(bucket_name)
        payload.update(compute_signed_kwargs)
        blob = bucket.get_blob(filename)
        if not blob:
            raise NoSuchBlobException(f"No such blob with filename {filename}")
        return blob.generate_signed_url(**payload)
    except Exception as e:
        log.warn(f"Problem with generating signed_url for filename='{filename}', bucket_name='{bucket_name}: {e}")
        return None
