import logging
from typing import List

from django.conf import settings


log = logging.getLogger(__name__)


def create_bucket(bucket_name: str) -> str:
    """https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html?highlight=create_bucket#S3.Client.create_bucket"""
    response = settings.S3_CLIENT.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={"LocationConstraint": "us-east-2"})
    return response.get("Location").strip("/")  # remove leading slash


def list_bucket_names() -> List[str]:
    """https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html?highlight=create_bucket#S3.Client.list_buckets"""
    response = settings.S3_CLIENT.list_buckets()

    # Get a list of all bucket names from the response
    return [bucket["Name"] for bucket in response["Buckets"]]
