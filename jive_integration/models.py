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
