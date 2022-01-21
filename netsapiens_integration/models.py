from django.db import models
from django.core.management.utils import get_random_secret_key

from django_extensions.db.fields import ShortUUIDField

from core.abstract_models import AuditTrailModel


class NetsapiensSubscriptionClient(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    voip_provider = models.ForeignKey("core.VoipProvider", on_delete=models.CASCADE)


class NetsapiensCallsSubscriptionEventExtract(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    netsapiens_subscription_client = models.ForeignKey(NetsapiensSubscriptionClient, null=True, on_delete=models.SET_NULL)
    # These max_lengths are best guesses based on Core1-phx's CdrDomain.201904_r table, unless otherwise specified
    # To be the truest extract we can make without using JSONField, making blank=True for CharFields and null=True for all others
    orig_callid = models.CharField(max_length=127, blank=True)  # 0_1063160652@192.168.168.127
    by_callid = models.CharField(max_length=127, blank=True)  # 20220119004825004745-8d8a5d555a2bdaa84182cb8f8d613b03
    term_callid = models.CharField(max_length=127, blank=True)  # 20220119004825004745-8d8a5d555a2bdaa84182cb8f8d613b03
    hostname = models.CharField(max_length=32, blank=True)  # core1-phx.peerlogic.com
    sessionId = models.CharField(max_length=63, blank=True)  # max_length based on NcsDomain.activecalls
    acr_id = models.CharField(max_length=255, blank=True)  # no basis found for length
    orig_leg_tag = models.CharField(max_length=127, blank=True)  # max_length based on NcsDomain.activecalls
    orig_ip = models.CharField(max_length=63, blank=True)
    orig_match = models.CharField(max_length=127, blank=True)
    orig_sub = models.CharField(max_length=63, blank=True)
    orig_domain = models.CharField(max_length=63, blank=True)
    orig_own_sub = models.CharField(max_length=63, blank=True)
    orig_own_domain = models.CharField(max_length=63, blank=True)
    orig_type = models.CharField(max_length=15, blank=True)
    orig_group = models.CharField(max_length=63, blank=True)
    orig_site = models.CharField(max_length=45, blank=True)  # max_length based on NcsDomain.activecalls
    orig_territory = models.CharField(max_length=45, blank=True)
    orig_from_uri = models.CharField(max_length=63, blank=True)
    orig_logi_uri = models.CharField(max_length=63, blank=True)
    orig_from_name = models.CharField(max_length=63, blank=True)
    orig_from_user = models.CharField(max_length=63, blank=True)
    orig_from_host = models.CharField(max_length=63, blank=True)
    orig_req_uri = models.CharField(max_length=63, blank=True)
    orig_req_user = models.CharField(max_length=63, blank=True)
    orig_req_host = models.CharField(max_length=63, blank=True)
    orig_to_uri = models.CharField(max_length=63, blank=True)
    orig_to_user = models.CharField(max_length=63, blank=True)
    orig_to_host = models.CharField(max_length=63, blank=True)
    by_action = models.CharField(max_length=31, blank=True)
    by_sub = models.CharField(max_length=63, blank=True)
    by_domain = models.CharField(max_length=63, blank=True)
    by_type = models.CharField(max_length=15, blank=True)  # max_length based on NcsDomain.activecalls
    by_group = models.CharField(max_length=63, blank=True)
    by_site = models.CharField(max_length=45, blank=True)
    by_territory = models.CharField(max_length=45, blank=True)
    by_uri = models.CharField(max_length=63, blank=True)
    term_leg_tag = models.CharField(max_length=255, blank=True)
    term_ip = models.CharField(max_length=63, blank=True)
    term_match = models.CharField(max_length=127, blank=True)
    term_sub = models.CharField(max_length=63, blank=True)
    term_domain = models.CharField(max_length=63, blank=True)
    term_own_sub = models.CharField(max_length=63, blank=True)
    term_own_domain = models.CharField(max_length=63, blank=True)
    term_type = models.CharField(max_length=15, blank=True)  # max_length based on NcsDomain.activecalls
    term_group = models.CharField(max_length=63, blank=True)
    term_site = models.CharField(max_length=45, blank=True)
    term_territory = models.CharField(max_length=45, blank=True)
    term_to_uri = models.CharField(max_length=63, blank=True)
    term_logi_uri = models.CharField(max_length=63, blank=True)
    time_start = models.DateTimeField(null=True)
    time_answer = models.DateTimeField(null=True)
    orig_id = models.CharField(max_length=42, blank=True)
    term_id = models.CharField(max_length=42, blank=True)
    by_id = models.CharField(max_length=42, blank=True)
    orig_call_info = models.CharField(max_length=255, blank=True)
    term_call_info = models.CharField(max_length=255, blank=True)
    route_to = models.CharField(max_length=255, blank=True)  # max_length based on NcsDomain.activecalls
    route_class = models.CharField(max_length=15, blank=True)  # max_length based on NcsDomain.activecalls
    media = models.CharField(max_length=63, blank=True)  # max_length based on NcsDomain.activecalls
    pac = models.CharField(max_length=31, blank=True)  # max_length based on NcsDomain.activecalls
    action = models.CharField(max_length=31, blank=True)  # max_length based on NcsDomain.activecalls
    action_parameter = models.CharField(max_length=127, blank=True)  # max_length based on NcsDomain.activecalls
    action_by = models.CharField(max_length=127, blank=True)  # max_length based on NcsDomain.activecalls
    notes = models.CharField(max_length=255, blank=True)  # max_length based on NcsDomain.activecalls
    time_begin = models.DateTimeField(null=True)  # max_length based on NcsDomain.conf_participants and that it starts with time
    time_refresh = models.CharField(max_length=63, blank=True)  # max_length based on NcsDomain.activecalls
    ts = models.DateTimeField(null=True)
    term_uri = models.CharField(max_length=255, blank=True)  # no basis found for length
    dnis = models.CharField(max_length=127, blank=True)  # max_length based on SiPbxDomain.callqueue_stat_cdr_helper
    orig_name = models.CharField(max_length=63, blank=True)  # max_length based on SiPbxDomain.callrequest_config
    ani = models.CharField(max_length=63, blank=True)  # max_length based on SiPbxDomain.ani_config and SiPbxDomain.ani_to_subscriber
    orig_user = models.CharField(max_length=255, blank=True)  # no basis found for length
    term_user = models.CharField(max_length=127, blank=True)  # max_length based on SiPbxDomain.registrar_update
    remove = models.CharField(max_length=255, blank=True)  # yes
