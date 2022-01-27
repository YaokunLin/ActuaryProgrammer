from django.db import models
from django.urls import reverse

from django_extensions.db.fields import ShortUUIDField

from core.abstract_models import AuditTrailModel


class NetsapiensAPICredentials(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    voip_provider = models.ForeignKey("core.VoipProvider", on_delete=models.CASCADE)

    api_url = models.CharField(max_length=2048, blank=True)
    client_id = models.CharField(max_length=64, blank=True)  # NsApi.oauth_clients.client_id
    client_secret = models.CharField(max_length=64, blank=True)  # NsApi.oauth_clients.client_secret
    username = models.CharField(max_length=63, blank=True)  # extension@domain = SiPbxDomain.subscriber_config.subscriber_login 
    password = models.CharField(max_length=255, blank=True)  # unknown, it's a guess, password hash may be 60 in length based upon SiPbxDomain.subscriber_config.pwd_hash

    active = models.BooleanField(null=True, blank=False, default=False)  # whether these credentials are active for usage


class NetsapiensSubscriptionClient(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    voip_provider = models.ForeignKey("core.VoipProvider", on_delete=models.CASCADE)

    @property
    def call_subscription_uri(self):
        return reverse("netsapiens:call-subscription", kwargs={"voip_provider_id": self.voip_provider.pk, "client_id": self.id})


class NetsapiensCallsSubscriptionEventExtract(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    netsapiens_subscription_client = models.ForeignKey(NetsapiensSubscriptionClient, null=True, on_delete=models.SET_NULL)
    # These max_lengths are best guesses based on Core1-phx's CdrDomain.201904_r table, unless otherwise specified
    # To be the truest extract we can make without using JSONField, making blank=True for CharFields and null=True for all others
    orig_callid = models.CharField(max_length=127, blank=True, null=True)  # 0_1063160652@192.168.168.127
    by_callid = models.CharField(max_length=127, blank=True, null=True)  # 20220119004825004745-8d8a5d555a2bdaa84182cb8f8d613b03
    term_callid = models.CharField(max_length=127, blank=True, null=True)  # 20220119004825004745-8d8a5d555a2bdaa84182cb8f8d613b03
    hostname = models.CharField(max_length=32, blank=True, null=True)  # core1-phx.peerlogic.com
    sessionId = models.CharField(max_length=63, blank=True, null=True)  # max_length based on NcsDomain.activecalls
    acr_id = models.CharField(max_length=255, blank=True, null=True)  # no basis found for length
    orig_leg_tag = models.CharField(max_length=127, blank=True, null=True)  # max_length based on NcsDomain.activecalls
    orig_ip = models.CharField(max_length=63, blank=True, null=True)
    orig_match = models.CharField(max_length=127, blank=True, null=True)
    orig_sub = models.CharField(max_length=63, blank=True, null=True)
    orig_domain = models.CharField(max_length=63, blank=True, null=True)
    orig_own_sub = models.CharField(max_length=63, blank=True, null=True)
    orig_own_domain = models.CharField(max_length=63, blank=True, null=True)
    orig_type = models.CharField(max_length=15, blank=True, null=True)
    orig_group = models.CharField(max_length=63, blank=True, null=True)
    orig_site = models.CharField(max_length=45, blank=True, null=True)  # max_length based on NcsDomain.activecalls
    orig_territory = models.CharField(max_length=45, blank=True, null=True)
    orig_from_uri = models.CharField(max_length=63, blank=True, null=True)
    orig_logi_uri = models.CharField(max_length=63, blank=True, null=True)
    orig_from_name = models.CharField(max_length=63, blank=True, null=True)
    orig_from_user = models.CharField(max_length=63, blank=True, null=True)
    orig_from_host = models.CharField(max_length=63, blank=True, null=True)
    orig_req_uri = models.CharField(max_length=63, blank=True, null=True)
    orig_req_user = models.CharField(max_length=63, blank=True, null=True)
    orig_req_host = models.CharField(max_length=63, blank=True, null=True)
    orig_to_uri = models.CharField(max_length=63, blank=True, null=True)
    orig_to_user = models.CharField(max_length=63, blank=True, null=True)
    orig_to_host = models.CharField(max_length=63, blank=True, null=True)
    by_action = models.CharField(max_length=31, blank=True, null=True)
    by_sub = models.CharField(max_length=63, blank=True, null=True)
    by_domain = models.CharField(max_length=63, blank=True, null=True)
    by_type = models.CharField(max_length=15, blank=True, null=True)  # max_length based on NcsDomain.activecalls
    by_group = models.CharField(max_length=63, blank=True, null=True)
    by_site = models.CharField(max_length=45, blank=True, null=True)
    by_territory = models.CharField(max_length=45, blank=True, null=True)
    by_uri = models.CharField(max_length=63, blank=True, null=True)
    term_leg_tag = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    term_ip = models.CharField(max_length=63, blank=True, null=True)
    term_match = models.CharField(max_length=127, blank=True, null=True)
    term_sub = models.CharField(max_length=63, blank=True, null=True)
    term_domain = models.CharField(max_length=63, blank=True, null=True)
    term_own_sub = models.CharField(max_length=63, blank=True, null=True)
    term_own_domain = models.CharField(max_length=63, blank=True, null=True)
    term_type = models.CharField(max_length=15, blank=True, null=True)  # max_length based on NcsDomain.activecalls
    term_group = models.CharField(max_length=63, blank=True, null=True)
    term_site = models.CharField(max_length=45, blank=True, null=True)
    term_territory = models.CharField(max_length=45, blank=True, null=True)
    term_to_uri = models.CharField(max_length=63, blank=True, null=True)
    term_logi_uri = models.CharField(max_length=63, blank=True, null=True)
    time_start = models.DateTimeField(null=True)
    time_answer = models.DateTimeField(null=True)
    orig_id = models.CharField(max_length=42, blank=True, null=True)
    term_id = models.CharField(max_length=42, blank=True, null=True)
    by_id = models.CharField(max_length=42, blank=True, null=True)
    orig_call_info = models.CharField(max_length=255, blank=True, null=True)
    term_call_info = models.CharField(max_length=255, blank=True, null=True)
    route_to = models.CharField(max_length=255, blank=True, null=True)  # max_length based on NcsDomain.activecalls
    route_class = models.CharField(max_length=15, blank=True, null=True)  # max_length based on NcsDomain.activecalls
    media = models.CharField(max_length=63, blank=True, null=True)  # max_length based on NcsDomain.activecalls
    pac = models.CharField(max_length=31, blank=True, null=True)  # max_length based on NcsDomain.activecalls
    action = models.CharField(max_length=31, blank=True, null=True)  # max_length based on NcsDomain.activecalls
    action_parameter = models.CharField(max_length=127, blank=True, null=True)  # max_length based on NcsDomain.activecalls
    action_by = models.CharField(max_length=127, blank=True, null=True)  # max_length based on NcsDomain.activecalls
    notes = models.CharField(max_length=255, blank=True, null=True)  # max_length based on NcsDomain.activecalls
    time_begin = models.DateTimeField(null=True)  # max_length based on NcsDomain.conf_participants and that it starts with time
    time_refresh = models.CharField(max_length=63, blank=True, null=True)  # max_length based on NcsDomain.activecalls
    ts = models.DateTimeField(null=True)
    term_uri = models.CharField(max_length=255, blank=True, null=True)  # no basis found for length
    dnis = models.CharField(max_length=127, blank=True, null=True)  # max_length based on SiPbxDomain.callqueue_stat_cdr_helper
    orig_name = models.CharField(max_length=63, blank=True, null=True)  # max_length based on SiPbxDomain.callrequest_config
    ani = models.CharField(max_length=63, blank=True, null=True)  # max_length based on SiPbxDomain.ani_config and SiPbxDomain.ani_to_subscriber
    orig_user = models.CharField(max_length=255, blank=True, null=True)  # no basis found for length
    term_user = models.CharField(max_length=127, blank=True, null=True)  # max_length based on SiPbxDomain.registrar_update
    remove = models.CharField(max_length=255, blank=True, null=True, db_index=True)  # yes


class NetsapiensCdr2Extract(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    netsapiens_subscription_client = models.ForeignKey(NetsapiensSubscriptionClient, null=True, on_delete=models.SET_NULL)
    peerlogic_call_id = models.CharField(blank=True, default="", max_length=22, db_index=True)  # maps to calls/models.py Call model's id
    # These max_lengths are best guesses based on Core1-phx's CdrDomain.201904_r table, unless otherwise specified
    # To be the truest extract we can make without using JSONField, making blank=True for CharFields and null=True for all others
    domain = models.CharField(max_length=63, blank=True, null=True)  # e.g. "pleasantdental-peoria"
    territory = models.CharField(max_length=45, blank=True, null=True)  # e.g. "Peerlogic"
    type = models.IntegerField(max_length=1, null=True)  # e.g. "1", based on CdrDomain.201904_d
    cdr_id = models.CharField(max_length=42, blank=True, null=True)  # e.g."1642816606d99fbc563c6f77ff6ab363a644d87c5b"
    orig_sub = models.CharField(max_length=42, blank=True, null=True)
    orig_from_uri = models.CharField(max_length=63, blank=True, null=True)  # e.g. "sip:4807984575@67.231.3.4"
    orig_from_name = models.CharField(max_length=63, blank=True, null=True)  # e.g. "PAULA MALLEY"
    orig_to_user = models.CharField(max_length=63, blank=True, null=True)  # e.g. "6232952005"
    orig_req_uri = models.CharField(max_length=63, blank=True, null=True)  # e.g. "sip:6232952005@core1-phx.peerlogic.com"
    orig_req_user = models.CharField(max_length=63, blank=True, null=True)  # e.g. "6232952005"
    by_sub = models.CharField(max_length=63, blank=True, null=True)  # e.g. "4001"
    term_sub = models.CharField(max_length=63, blank=True, null=True)  # e.g. "1100"
    term_to_uri = models.CharField(max_length=63, blank=True, null=True)  # e.g. "sip:1100@pleasantdental-peoria"
    time_start = models.DateTimeField(null=True)  # e.g. "1642816606"
    time_answer = models.DateTimeField(null=True)  # e.g. "1642816610"
    time_release = models.DateTimeField(null=True)  # e.g. "1642816660"
    duration = models.DurationField(null=True)  # e.g. "54"
    time_talking = models.DurationField(null=True)  # e.g. "54"
    hide = models.IntegerField(max_length=5, null=True)  # e.g. "0", based on CdrDomain.201904_d
    tag = models.CharField(max_length=45, blank=True, null=True)  # based on CdrDomain.201904_d
    # Left over CDR R values
    # REDUNDANT: "id": "1642816606d99fbc563c6f77ff6ab363a644d87c5b"
    hostname = models.CharField(max_length=32, blank=True, null=True)  # e.g. "core1-phx.peerlogic.com"
    mac = models.CharField(max_length=18, blank=True, null=True)  # e.g. "24:6E:96:10:C2:B8"
    cdr_index = models.IntegerField(max_length=11, null=True)  # e.g. "1"
    orig_callid = models.CharField(max_length=127, blank=True, null=True, db_index=True)  # e.g. "17613391_133144556@67.231.3.4"
    orig_ip = models.CharField(max_length=63, blank=True, null=True)  # e.g. "67.231.3.4"
    orig_match = models.CharField(max_length=127, blank=True, null=True)  # e.g. "sip*@67.231.3.4"
    # REDUNDANT: "orig_sub": null
    orig_domain = models.CharField(max_length=63, blank=True, null=True)
    orig_group = models.CharField(max_length=63, blank=True, null=True)
    # REDUNDANT: "orig_from_uri": "sip:4807984575@67.231.3.4"
    # REDUNDANT: "orig_from_name": "PAULA MALLEY"
    orig_from_user = models.CharField(max_length=63, blank=True, null=True)  # e.g. "4807984575"
    orig_from_host = models.CharField(max_length=63, blank=True, null=True)  # e.g. "67.231.3.4"
    # REDUNDANT: "orig_req_uri": "sip:6232952005@core1-phx.peerlogic.com"
    # REDUNDANT: "orig_req_user": "6232952005"
    orig_req_host = models.CharField(max_length=63, blank=True, null=True)  # e.g. "core1-phx.peerlogic.com"
    orig_to_uri = models.CharField(max_length=63, blank=True, null=True)  # e.g. "sip:6232952005@core1-phx.peerlogic.com"
    # REDUNDANT: "orig_to_user": "6232952005"
    orig_to_host = models.CharField(max_length=63, blank=True, null=True)  # e.g. "core1-phx.peerlogic.com"
    by_action = models.CharField(max_length=31, blank=True, null=True)  # e.g. "QueueSDispatch"
    # REDUNDANT: "by_sub": "4001"
    by_domain = models.CharField(max_length=63, blank=True, null=True)  # e.g. "pleasantdental-peoria"
    by_group = models.CharField(max_length=63, blank=True, null=True)  # e.g. "Front Office"
    by_uri = models.CharField(max_length=63, blank=True, null=True)
    by_callid = models.CharField(max_length=127, blank=True, null=True, db_index=True)  # e.g. "20220122015646001363-8d8a5d555a2bdaa84182cb8f8d613b03"
    term_callid = models.CharField(max_length=127, blank=True, null=True, db_index=True)  # e.g. "20220122015647001366-8d8a5d555a2bdaa84182cb8f8d613b03"
    term_ip = models.CharField(max_length=63, blank=True, null=True)  # e.g. "98.174.249.67"
    term_match = models.CharField(max_length=127, blank=True, null=True)  # e.g. "sip:1100@pleasantdental-peoria"
    # REDUNDANT: "term_sub": "1100"
    term_domain = models.CharField(max_length=63, blank=True, null=True)  # e.g. "pleasantdental-peoria"
    # REDUNDANT: "term_to_uri": "sip:1100@pleasantdental-peoria"
    term_group = models.CharField(max_length=63, blank=True, null=True)  # e.g. "Front Office"
    # REDUNDANT: "time_start": "1642816607"
    time_ringing = models.DateTimeField(null=True)  # e.g. "1642816607"
    # REDUNDANT: "time_answer": "1642816610"
    # REDUNDANT: "time_release": "1642816660"
    # REDUNDANT: "time_talking": "50"
    time_holding = models.DurationField(null=True)  # e.g. "0"
    duration = models.DurationField(null=True)  # e.g. "50"
    time_insert = models.DateTimeField(null=True)  # e.g.
    time_disp = models.DateTimeField(null=True)  # e.g.
    release_code = models.CharField(max_length=15, blank=True, null=True)  # e.g. "end"
    release_text = models.CharField(max_length=63, blank=True, null=True, db_index=True)  # e.g. "Orig: Bye"
    codec = models.CharField(max_length=15, blank=True, null=True)  # e.g. "PCMU"
    rly_prt_0 = models.CharField(max_length=15, blank=True, null=True)  # e.g. "26120"
    rly_prt_a = models.CharField(max_length=31, blank=True, null=True)  # e.g. "98.174.249.67:11796"
    rly_prt_b = models.CharField(max_length=31, blank=True, null=True)  # e.g. "67.231.0.123:15772"
    rly_cnt_a = models.CharField(max_length=15, blank=True, null=True)  # e.g. "424668"
    rly_cnt_b = models.CharField(max_length=15, blank=True, null=True)  # e.g. "425700"
    image_codec = models.CharField(max_length=15, blank=True, null=True)
    image_prt_0 = models.CharField(max_length=31, blank=True, null=True)
    image_prt_a = models.CharField(max_length=31, blank=True, null=True)
    image_prt_b = models.CharField(max_length=31, blank=True, null=True)
    image_cnt_a = models.CharField(max_length=15, blank=True, null=True)
    image_cnt_b = models.CharField(max_length=15, blank=True, null=True)
    video_codec = models.CharField(max_length=15, blank=True, null=True)
    video_prt_0 = models.CharField(max_length=15, blank=True, null=True)
    video_prt_a = models.CharField(max_length=31, blank=True, null=True)
    video_prt_b = models.CharField(max_length=31, blank=True, null=True)
    video_cnt_a = models.CharField(max_length=15, blank=True, null=True)
    video_cnt_b = models.CharField(max_length=15, blank=True, null=True)
    disp_type = models.CharField(max_length=32, blank=True, null=True)
    disposition = models.CharField(max_length=15, blank=True, null=True)
    reason = models.CharField(max_length=64, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    pac = models.CharField(max_length=31, blank=True, null=True)
    orig_logi_uri = models.CharField(max_length=63, blank=True, null=True)  # e.g. "sip:4807984575@67.231.3.4"
    term_logi_uri = models.CharField(max_length=63, blank=True, null=True)  # e.g. "sip:16232952005@pleasantdental-peoria"
    batch_tim_beg = models.IntegerField(max_length=16, null=True)  # e.g. "1642816606"
    batch_tim_ans = models.IntegerField(max_length=16, null=True)  # e.g. "1642816606"
    batch_hold = models.IntegerField(max_length=15, null=True)  # e.g. "0"
    batch_dura = models.IntegerField(max_length=15, null=True)  # e.g. "54"
    orig_id = models.CharField(max_length=63, blank=True, null=True)  # e.g. "4807984575"
    term_id = models.CharField(max_length=63, blank=True, null=True)  # e.g. "6232952005"
    by_id = models.CharField(max_length=63, blank=True, null=True)  # e.g. "6232952005"
    route_to = models.CharField(max_length=255, blank=True, null=True)  # e.g. "sip:*@*"
    route_class = models.CharField(max_length=15, blank=True, null=True)  # e.g. "0"
    orig_territory = models.CharField(max_length=45, blank=True, null=True)
    orig_site = models.CharField(max_length=45, blank=True, null=True)
    by_site = models.CharField(max_length=45, blank=True, null=True)
    by_territory = models.CharField(max_length=45, blank=True, null=True)  # e.g. "Peerlogic"
    term_territory = models.CharField(max_length=45, blank=True, null=True)  # e.g. "Peerlogic"
    term_site = models.CharField(max_length=45, blank=True, null=True)
