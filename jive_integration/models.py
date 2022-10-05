from datetime import datetime

from django.db import models
from django_extensions.db.fields import ShortUUIDField

from core.abstract_models import AuditTrailModel


class JiveConnection(AuditTrailModel):
    """
    Represents the link between a user and all the associated models required to receive call events.  The refresh token
    from the user's inital authentication is stored and used to an access token for interfacing with the Jive API.
    """

    id = ShortUUIDField(primary_key=True, editable=False)

    refresh_token = models.TextField(blank=True)
    practice_telecom = models.ForeignKey("core.PracticeTelecom", null=True, on_delete=models.SET_NULL)

    last_sync = models.DateTimeField(null=False, blank=False, default=datetime.min.isoformat())
    active = models.BooleanField(null=True, blank=False, default=True)


class JiveChannel(models.Model):
    """
    Channels represent a destination to deliver events from the Jive API to.  Channels define where events are delivered.
    Channels have a limited lifespan but can be refreshed to extend it.  When a channel is created a user defined
    signature is set and will be included with every request.  Channels are linked to a user through the `JiveConnection`
    and can have many resourced linked to them.  Any dependent resource will cascade deletes when a channel is deleted.
    """

    id = ShortUUIDField(primary_key=True, editable=False)

    connection = models.ForeignKey(JiveConnection, null=False, on_delete=models.CASCADE)

    name = ShortUUIDField(unique=True)
    source_jive_id = models.CharField(unique=True, max_length=256)
    signature = models.CharField(max_length=64, unique=True, blank=False, null=False)
    expires_at = models.DateTimeField(null=False)
    active = models.BooleanField(default=True, null=False)


class JiveSession(models.Model):
    """
    Session represent a series of objects that we would like to be notified of events for.  Sessions are linked to
    channels in the Jive API as a vector for events.
    """

    id = ShortUUIDField(primary_key=True, editable=False)

    channel = models.ForeignKey(JiveChannel, null=False, on_delete=models.CASCADE)

    url = models.URLField(null=False)


class JiveLine(models.Model):
    """
    Represents a phone number associated with the user's Jive account.  Most Jive API endpoints require
    a reference to the associated organization id to reference a line. Lines are linked to a user's account
    though the session.
    """

    id = ShortUUIDField(primary_key=True, editable=False)

    session = models.ForeignKey(JiveSession, null=True, on_delete=models.CASCADE)

    source_jive_id = models.CharField(max_length=64, blank=False, null=False, unique=True)
    source_organization_jive_id = models.CharField(max_length=64, blank=False, null=False, unique=True)


class JiveCallPartial(models.Model):
    """
    Used to track the start time of a call until the call is concluded.
    """

    id = ShortUUIDField(primary_key=True, editable=False)

    start_time = models.DateTimeField()
    source_jive_id = models.CharField(null=False, blank=False, max_length=255)


class JiveSubscriptionEventExtract(AuditTrailModel):
    """
    Raw event from Jive Subscription, first saved to JSONField, and then into columns.

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
    jive_extract = models.JSONField()

    # Lengths except where commented with context are arbitrary due to not knowing the contract
    jive_type = models.CharField(max_length=128, db_index=True)
    sub_id = models.CharField(max_length=36, db_index=True)  # uuid stored as a string
    # TODO: verify these look right
    old_id = models.CharField(max_length=36, db_index=True)  # uuid stored as a string
    new_id = models.CharField(max_length=36, db_index=True)  # uuid stored as a string
    entity_id = models.CharField(max_length=128, db_index=True)
    data_leg_id = models.CharField(max_length=36, db_index=True)  # uuid stored as a string
    data_created = models.DateTimeField()
    data_participant = models.CharField(max_length=128)
    data_callee_name = models.CharField(max_length=128)
    data_callee_number = models.CharField(max_length=128)
    data_caller_name = models.CharField(max_length=128)
    data_caller_number = models.CharField(max_length=128)
    data_direction = models.CharField(max_length=128)
    data_state = models.CharField(max_length=128)
    data_ani = models.CharField(max_length=128)
    data_recordings_extract = models.JSONField()  # May not want this since it's found in jive_extract?
    data_is_click_to_call = models.BooleanField()
    data_originator_id = models.CharField(max_length=36)
    data_originator_organization_id = models.CharField(max_length=36)
