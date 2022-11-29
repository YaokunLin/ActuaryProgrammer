from datetime import datetime
import logging
from typing import Dict
from django.conf import settings

from django.db import models
from django_extensions.db.fields import ShortUUIDField

from core.abstract_models import AuditTrailModel
from core.aws_iam_helpers import attach_user_policy, create_access_key, create_user, create_call_recording_iam_policy_for_bucket
from core.aws_s3_helpers import create_bucket
from core.models import PracticeTelecom
from jive_integration.field_choices import JiveEventTypeChoices, JiveLegStateChoices

log = logging.getLogger(__name__)


class JiveAPICredentials(AuditTrailModel):
    """
    Represents the link between a user and all the associated models required to receive call events.  The refresh token
    from the user's inital authentication is stored and used to an access token for interfacing with the Jive API.
    """

    id = ShortUUIDField(primary_key=True, editable=False)
    # token_type = "Bearer"
    access_token = models.TextField(blank=True)
    refresh_token = models.TextField(blank=True)
    scope = models.TextField(blank=True)
    # firstName
    # lastName
    account_key = models.CharField(max_length=20, blank=True)
    organizer_key = models.CharField(max_length=20, blank=True)
    # version
    # account_type
    email = models.TextField(blank=True)  # is the user principal (email) with super admin privileges
    practice_telecom = models.ForeignKey("core.PracticeTelecom", null=True, on_delete=models.SET_NULL)

    last_sync = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)


class JiveAWSRecordingBucket(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    # TODO: deprecate
    jive_api_credentials = models.OneToOneField(JiveAPICredentials, on_delete=models.SET_NULL, null=True, related_name="bucket")
    practice_telecom = models.OneToOneField(PracticeTelecom, on_delete=models.SET_NULL, null=True, related_name="bucket")
    bucket_name = models.CharField(blank=True, max_length=63)  # https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucketnamingrules.html
    access_key_id = models.CharField(blank=True, max_length=128)  # https://docs.aws.amazon.com/IAM/latest/APIReference/API_AccessKey.html
    username = models.CharField(blank=True, max_length=64)  # https://docs.aws.amazon.com/IAM/latest/APIReference/API_User.html
    policy_arn = models.CharField(blank=True, max_length=2048)  # https://docs.aws.amazon.com/IAM/latest/APIReference/API_Policy.html

    @property
    def aws_short_resource_name(self) -> str:
        """
        Used for all resources in aws related to this model to refer back to this model

        Use jive, then ID at beginning and then normal domain heirarchy employed
        by the dependency flow for ease
        This is for easy searchability within the S3 and IAM consoles
        """

        # * buckets must be 63 characters or less
        # * usernames must be 64 characters or less
        # we only have room for 2 ids each 22 characters for a total of 50 chars
        practice = self.practice_telecom.practice
        return f"jive-{practice.id}-{self.id}"

    def generate_aws_bucket_name(self) -> str:
        """
        Used for nearly everything in aws to refer back to this model in our database

        Use jive, then ID at beginning and then normal domain heirarchy employed
        by the dependency flow for ease
        This is for easy searchability within the S3 and IAM consoles
        """

        # must be lowercase
        # must be 63 characters or less - only have room for 2 ids each 22 characters for a total of 50 chars
        return self.aws_short_resource_name.lower()

    @property
    def aws_long_resource_name(self) -> str:
        """
        Used for nearly everything in aws to refer back to this model in our database

        Use jive, then ID at beginning and then normal domain heirarchy employed
        by the dependency flow for ease
        This is for easy searchability within the S3 and IAM consoles

        Could add 1 more 22 character shortuuid to this if we would like
        """

        return f"jive-{self.id}-{self.practice_telecom.id}-{self.practice_telecom.practice.id}"

    def create_bucket(self) -> str:
        """Burn in the bucket name"""
        bucket_name = self.generate_aws_bucket_name()
        create_bucket(bucket_name=bucket_name)
        self.bucket_name = bucket_name
        self.save()

    def generate_credentials(self) -> Dict[str, str]:
        user = create_user(username=self.aws_short_resource_name)
        self.username = user.UserName
        policy = create_call_recording_iam_policy_for_bucket(policy_name=self.aws_long_resource_name, bucket_name=self.bucket_name)
        self.policy_arn = policy.Arn
        attach_user_policy(policy_arn=self.policy_arn, username=self.username)
        access_key = create_access_key(username=self.username)
        self.access_key_id = access_key.AccessKeyId
        log.info(f"Saving recording bucket info to the database with self.__dict__={self.__dict__}")
        self.save()
        log.info(f"Saved recording bucket info to the database with self.__dict__={self.__dict__}")

        # Do not save off the secret key, only return it
        return {"aws_bucket_name": self.bucket_name, "aws_access_key": self.access_key_id, "aws_secret_access_key": access_key.SecretAccessKey}

    def delete_credentials(self):
        """TODO: implement for cleanup
        Detach Policy
        Delete Policy
        Delete Access Key
        Delete User
        """

        pass

    def regenerate_credentials(self):
        """TODO: implement for inevitable issues"""
        pass


class JiveChannel(AuditTrailModel):
    """
    Channels represent a destination to deliver events from the Jive API to.  Channels define where events are delivered.
    Channels have a limited lifespan but we can extend it.  When a channel is created a user defined signature is set
    and will be included with every request.  Channels are linked to a user through the `JiveAPICredentials`
    and can have many resources linked to them.  Any dependent resource will cascade deletes when a channel is deleted.

    https://developer.goto.com/GoToConnect#section/Getting-Started/Step-Two:-Open-a-WebSocket-or-Use-Your-Notification-Channel
    """

    id = ShortUUIDField(primary_key=True, editable=False)

    jive_api_credentials = models.ForeignKey(JiveAPICredentials, on_delete=models.CASCADE)

    # TODO: link to practice_telecom instead
    # practice_telecom = models.ForeignKey("core.PracticeTelecom", null=True, on_delete=models.SET_NULL)

    name = ShortUUIDField(unique=True)
    source_jive_id = models.CharField(unique=True, max_length=256)
    signature = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    active = models.BooleanField(default=True)


class JiveSession(AuditTrailModel):
    """
    Session represent a series of objects that we would like to be notified of events for.  Sessions are linked to
    channels in the Jive API as a vector for events.
    https://developer.goto.com/GoToConnect#section/Getting-Started/Step-One:-Creating-a-Session
    """

    id = ShortUUIDField(primary_key=True, editable=False)

    channel = models.ForeignKey(JiveChannel, on_delete=models.CASCADE)

    url = models.URLField()


class JiveLine(AuditTrailModel):
    """
    Represents a phone number associated with the user's Jive account.  Most Jive API endpoints require
    a reference to the associated organization id to reference a line. Lines are linked to a user's account
    though the session.
    https://developer.goto.com/GoToConnect#section/Getting-Started/Step-Three:-Subscribe
    """

    id = ShortUUIDField(primary_key=True, editable=False)

    session = models.ForeignKey(JiveSession, null=True, on_delete=models.CASCADE)

    source_jive_id = models.CharField(max_length=64, unique=True)
    source_organization_jive_id = models.CharField(max_length=64)


class JiveSubscriptionEventExtract(AuditTrailModel):
    """
    Raw event from Jive Subscription, first saved to JSONField, and then into columns.

    https://developer.goto.com/GoToConnect#section/Subscription-Types/Dialog

    Inbound
    {
        'type': 'withdraw',
        'subId': 'cc23a545-9594-4f5f-b59d-d9022aba6ecb',
        'entityId': '625957634',
        'data': {
            'legId': '15c2c70d-b9bb-4128-aef3-b65bd4f8d5a6',
            'created': 1663623167457,
            'participant': '31hyS3uK0ODIr0QXf2jUF9VyUeBjp0',
            'callee': {'name': 'Research Development', 'number': '1000'},
            'caller': {'name': 'WIRELESS CALLER', 'number': '4806525408'},
            'direction': 'recipient',
            'state': 'HUNGUP',
            'ani': '+15203759246 <+15203759246>',
            'recordings': [
                {
                    'filename': 'MjAyMi0wOS0xOVQxNTMyNDd+Y2FsbH4rMTQ4MDY1MjU0MDh+KzE1MjAzNzU5MjQ2fjQ5ZTBmZWQxLTQ3OWQtNDYzZi04OWI3LWI0ODFkZTkwY2UwOS53YXY='
                }
            ],
            'isClickToCall': False,
            'originatorId': '80793972-282f-439c-9cc1-29ff0446eac6',
            'originatorOrganizationId': 'af93983c-ec29-4aca-8516-b8ab36b587d1'
        }
    }

    Outbound
    {
        'type': 'withdraw', 'subId': 'cc23a545-9594-4f5f-b59d-d9022aba6ecb',
        'entityId': '627872218',
        'data': {
            'legId': '0ea9e26b-df04-43fb-921c-bdd89bbe86b8',
            'created': 1663623816968,
            'participant': '31hyS3uK0ODIr0QXf2jUF9VyUeBjp0',
            'callee': {'name': 'Unknown', 'number': '4806525408'},
            'caller': {'name': 'Research Development', 'number': '1000'},
            'direction': 'initiator',
            'state': 'HUNGUP',
            'recordings': [
                {
                    'filename': 'MjAyMi0wOS0xOVQxNTQzMzZ+Y2FsbH4xMDAwfjQ4MDY1MjU0MDh+MDkwOGFiYjgtMDRmZS00NWJiLTlmMTItYzJhYzc1NDc1ZTNlLndhdg=='
                }
            ],
            'isClickToCall': False,
            'originatorId': '0ea9e26b-df04-43fb-921c-bdd89bbe86b8',
            'originatorOrganizationId': 'af93983c-ec29-4aca-8516-b8ab36b587d1'
        }
    }
    """

    id = ShortUUIDField(primary_key=True, editable=False)
    peerlogic_call_id = models.CharField(
        blank=True, default="", max_length=22, db_index=True
    )  # maps to calls/models.py Call model's id (non-fk to keep these segregated)
    peerlogic_call_partial_id = models.CharField(
        blank=True, default="", max_length=22, db_index=True
    )  # maps to calls/models.py CallPartial model's id (non-fk to keep these segregated)
    jive_channel = models.ForeignKey(JiveChannel, null=True, on_delete=models.SET_NULL)
    jive_extract = models.JSONField()

    # Lengths except where commented with context are arbitrary due to not knowing the contract
    jive_type = models.CharField(
        max_length=16, db_index=True, choices=JiveEventTypeChoices.choices
    )  # the type of the event either announce, replace, withdraw and keepalive
    sub_id = models.CharField(max_length=36, db_index=True)  # uuid stored as a string
    old_id = models.CharField(max_length=36, db_index=True)  # uuid stored as a string
    new_id = models.CharField(max_length=36, db_index=True)  # uuid stored as a string
    entity_id = models.CharField(max_length=128)  # 6 digit number
    data_leg_id = models.CharField(
        max_length=36, db_index=True
    )  # the unique ID for this call state snapshot, related to the line on a particular device. In case you have multiple devices on the same line (eg. a soft-phone, and a hard-phone), you would receive multiple events with different legId. If the originatorId is the same for both events, they belong to the same call.
    data_created = models.DateTimeField(db_index=True)  # the Unix timestamp, in ms, at which the call reflected by this state snapshot was created
    data_participant = models.CharField(max_length=128)  # unique string - address of record (SIP username)
    data_callee_name = models.CharField(max_length=128)  # name of the entity receiving the call User's name, depending on call direction
    data_callee_number = models.CharField(max_length=128)  # 4 digit extension or telephone number, depending on call direction
    data_caller_name = models.CharField(max_length=128)  # Caller ID or User's name, depending on call direction
    data_caller_number = models.CharField(max_length=128)  # 4 digit extension or telephone number, depending on call direction
    data_direction = models.CharField(max_length=128)  # initiator or recipient
    data_state = models.CharField(
        max_length=16, db_index=True, choices=JiveLegStateChoices.choices
    )  # the current state of the call from a telephony standpoint. Note that more than one BRIDGED <-> UNBRIDGED cycles are possible.
    # * CREATED - event that is produced when a new leg is created.
    # * RINGING - event that is produced when a leg begins ringing.
    # * ANSWERED - event that is produced when a leg gets answered.
    # * BRIDGED - event that is produced when a leg gets connected to something.
    # * UNBRIDGED - event that is produced when a leg gets disconnected from something.
    # * HUNGUP - event that is produced when an existing leg gets destroyed.
    data_ani = models.CharField(
        max_length=128
    )  # the origination telephone number. This is the first number the call was made to. The field is populated when the call hits a call queue. The ANI is not related to the caller ID such as call display. This field is useful for tracking the number the caller originally called, regardless of transfers and other call changes - allows you to correlate incoming calls to marketing campaigns with a specific phone number for example.
    data_recordings_extract = models.JSONField()  # TODO: May not want this since it's found in jive_extract?
    data_is_click_to_call = models.BooleanField(
        blank=True
    )  # Boolean value, true if the call was initiated by Click-to-Call flow, false otherwise - blank a lot
    data_originator_id = models.CharField(max_length=36, db_index=True)  # unique id of the entity that triggered the creation of this leg
    data_originator_organization_id = models.CharField(max_length=36, db_index=True)  # organization id for the Jive account shared by multiple users
