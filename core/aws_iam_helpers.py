import json
import logging
from typing import Dict

from django.conf import settings

from core.pydantic_models.aws_models import AccessKey, IAMPolicy, User

log = logging.getLogger(__name__)


def create_user(username: str) -> User:
    """https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/iam.html#IAM.Client.create_user"""
    log.info(f"AWS: Creating user with {username}")
    response = settings.IAM_CLIENT.create_user(UserName=username)
    log.info(f"AWS: Created user with {username}. response='{response}'")
    return User(**response.get("User"))


def create_call_recording_iam_policy_for_bucket(policy_name: str, bucket_name: str) -> IAMPolicy:
    """https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/iam.html#IAM.Client.create_policy"""
    s3_managed_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "ListObjectsInBucket",
                "Effect": "Allow",
                "Action": [
                    "s3:ListBucket",
                ],
                "Resource": f"arn:aws:s3:::{bucket_name}",
                "Condition": {"StringNotEquals": {"s3:x-amz-acl": ["public-read"]}},
            },
            {
                "Sid": "CallRecordingObjectActions",
                "Effect": "Allow",
                "Action": [
                    "s3:AbortMultipartUpload",
                    "s3:PutObject",
                    "s3:PutObjectAcl",
                    "s3:GetObject",
                    "s3:GetObjectAcl",
                ],
                "Resource": f"arn:aws:s3:::{bucket_name}/*",
                "Condition": {"StringNotEquals": {"s3:x-amz-acl": ["public-read"]}},
            },
        ],
    }

    log.info(f"AWS: Creating recording bucket iam policy with policy_name='{policy_name}', bucket_name='{bucket_name}'")
    response = settings.IAM_CLIENT.create_policy(PolicyName=policy_name, PolicyDocument=json.dumps(s3_managed_policy))
    log.info(f"AWS: Created recording bucket iam policy with policy_name='{policy_name}', bucket_name='{bucket_name}', response='{response}'")
    return IAMPolicy(**response.get("Policy", {}))


def attach_user_policy(policy_arn: str, username: str) -> Dict:
    """https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/iam.html#IAM.Client.attach_user_policy"""
    log.info(f"AWS: Attaching iam policy with policy_arn='{policy_arn}', username='{username}'")
    response = settings.IAM_CLIENT.attach_user_policy(UserName=username, PolicyArn=policy_arn)
    log.info(f"AWS: Attached iam policy with policy_arn='{policy_arn}', username='{username}', response='{response}'")
    return response  # only response metadata is returned according to the docs, so no pydantic model ¯\_(ツ)_/¯


def detach_user_policy(policy_arn: str, username: str) -> Dict:
    """https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/iam.html#IAM.Client.detach_user_policy"""
    log.info(f"AWS: Detaching iam policy with policy_arn='{policy_arn}', username='{username}'")
    response = settings.IAM_CLIENT.detach_user_policy(UserName=username, PolicyArn=policy_arn)
    log.info(f"AWS: Detached iam policy with policy_arn='{policy_arn}', username='{username}', response='{response}'")
    return response  # only response metadata is returned according to the docs, so no pydantic model ¯\_(ツ)_/¯


def delete_call_recording_iam_policy_for_bucket(policy_arn: str, bucket_name: str) -> Dict:
    """
    https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/iam.html#IAM.Client.delete_policy

    bucket name included for logging
    """

    log.info(f"AWS: Deleting recording bucket iam policy with policy_arn='{policy_arn}', bucket_name='{bucket_name}'")
    response = settings.IAM_CLIENT.delete_policy(PolicyArn=policy_arn)
    log.info(f"AWS: Deleted recording bucket iam policy with policy_arn='{policy_arn}', bucket_name='{bucket_name}', response='{response}'")
    return response


def delete_access_key(access_key_id: str, username: str) -> Dict:
    """
    https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/iam.html#IAM.Client.delete_access_key
    """

    log.info(f"AWS: Deleting access key with access_key_id='{access_key_id}', username='{username}'")
    response = settings.IAM_CLIENT.delete_access_key(UserName=username, AccessKeyId=access_key_id)
    log.info(f"AWS: Deleted access key with access_key_id='{access_key_id}', username='{username}', response='{response}'")
    return response


def delete_user(username: str) -> Dict:
    """
    https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/iam.html#IAM.Client.delete_user
    """

    log.info(f"AWS: Deleting user with username='{username}'")
    response = settings.IAM_CLIENT.delete_user(UserName=username)
    log.info(f"AWS: Deleted user with username='{username}', response='{response}'")
    return response


def create_access_key(username: str) -> AccessKey:
    log.info(f"AWS: Creating access key for username='{username}'")
    response = settings.IAM_CLIENT.create_access_key(
        UserName=username,
    )
    log.info(f"AWS: Created access key for username='{username}', response='{response}'")
    return AccessKey(**response.get("AccessKey", {}))


if __name__ == "__main__":
    """Only run when from command line / scripted."""
    create_user("test-s3-user")
    create_call_recording_iam_policy_for_bucket("test-s3-user", "plapi-test-bucket-foo")
    attach_user_policy(policy_arn="arn:aws:iam::020628457151:policy/test-s3-user", username="test-s3-user")
    create_access_key("test-s3-user")
