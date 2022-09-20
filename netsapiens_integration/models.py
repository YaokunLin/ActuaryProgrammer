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
    password = models.CharField(max_length=255, blank=True)  # unknown, it's a guess, password hash may be 60 based upon SiPbxDomain.subscriber_config.pwd_hash

    active = models.BooleanField(null=True, blank=False, default=False)  # whether these credentials are active for usage

    class Meta:
        verbose_name_plural = "NetsapiensAPICredentials"


class NetsapiensCallSubscription(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    source_id = models.CharField(
        max_length=32, blank=True, default="", help_text=("Subscription ID for Netsapiens on the Voip Provider's side. The source of the data / events")
    )
    practice_telecom = models.ForeignKey("core.PracticeTelecom", null=True, on_delete=models.SET_NULL)  # keep call subscriptions and their ids forever

    active = models.BooleanField(null=True, blank=False, default=True)  # call subscription is active and should be receiving data

    @property
    def call_subscription_uri(self):
        return reverse("netsapiens:call-subscription-event-receiver", kwargs={"practice_telecom_id": self.practice_telecom.pk, "call_subscription_id": self.id})


class NetsapiensCallSubscriptionEventExtract(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    netsapiens_call_subscription = models.ForeignKey(NetsapiensCallSubscription, null=False, on_delete=models.RESTRICT)
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
    orig_sub = models.CharField(max_length=127, blank=True, null=True)  # length modified 2022-06-24 to fix 63 char error in prod
    orig_domain = models.CharField(max_length=127, blank=True, null=True)  # length modified 2022-06-24 to fix 63 char error in prod
    orig_own_sub = models.CharField(max_length=127, blank=True, null=True)  # length modified 2022-06-24 to fix 63 char error in prod
    orig_own_domain = models.CharField(max_length=127, blank=True, null=True)  # length modified 2022-06-24 to fix 63 char error in prod
    orig_type = models.CharField(max_length=15, blank=True, null=True)
    orig_group = models.CharField(max_length=127, blank=True, null=True)  # length modified 2022-06-24 to fix 63 char error in prod
    orig_site = models.CharField(max_length=45, blank=True, null=True)  # length modified 2022-06-24 to fix 63 char error in prod
    orig_territory = models.CharField(max_length=45, blank=True, null=True)
    orig_from_uri = models.CharField(max_length=127, blank=True, null=True)  # length modified 2022-06-24 to fix 63 char error in prod
    orig_logi_uri = models.CharField(max_length=127, blank=True, null=True)  # length modified 2022-06-24 to fix 63 char error in prod
    orig_from_name = models.CharField(max_length=127, blank=True, null=True)  # length modified 2022-06-24 to fix 63 char error in prod
    orig_from_user = models.CharField(max_length=127, blank=True, null=True)  # length modified 2022-06-24 to fix 63 char error in prod
    orig_from_host = models.CharField(max_length=127, blank=True, null=True)  # length modified 2022-06-24 to fix 63 char error in prod
    orig_req_uri = models.CharField(max_length=127, blank=True, null=True)  # length modified 2022-06-24 to fix 63 char error in prod
    orig_req_user = models.CharField(max_length=127, blank=True, null=True)  # length modified 2022-06-24 to fix 63 char error in prod
    orig_req_host = models.CharField(max_length=127, blank=True, null=True)  # length modified 2022-06-24 to fix 63 char error in prod
    orig_to_uri = models.CharField(max_length=127, blank=True, null=True)  # length modified 2022-06-24 to fix 63 char error in prod
    orig_to_user = models.CharField(max_length=127, blank=True, null=True)  # length modified 2022-06-24 to fix 63 char error in prod
    orig_to_host = models.CharField(max_length=127, blank=True, null=True)  # length modified 2022-06-24 to fix 63 char error in prod
    by_action = models.CharField(max_length=31, blank=True, null=True)
    by_sub = models.CharField(max_length=127, blank=True, null=True)  # length modified 2022-06-24 to fix 63 char error in prod
    by_domain = models.CharField(max_length=127, blank=True, null=True)  # length modified 2022-06-24 to fix 63 char error in prod
    by_type = models.CharField(max_length=15, blank=True, null=True)  # length modified 2022-06-24 to fix 63 char error in prod
    by_group = models.CharField(max_length=127, blank=True, null=True)  # length modified 2022-06-24 to fix 63 char error in prod
    by_site = models.CharField(max_length=45, blank=True, null=True)
    by_territory = models.CharField(max_length=45, blank=True, null=True)
    by_uri = models.CharField(max_length=127, blank=True, null=True)  # length modified 2022-06-24 to fix 63 char error in prod
    term_leg_tag = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    term_ip = models.CharField(max_length=63, blank=True, null=True)
    term_match = models.CharField(max_length=127, blank=True, null=True)
    term_sub = models.CharField(max_length=127, blank=True, null=True)  # length modified 2022-06-24 to fix 63 char error in prod
    term_domain = models.CharField(max_length=127, blank=True, null=True)  # length modified 2022-06-24 to fix 63 char error in prod
    term_own_sub = models.CharField(max_length=127, blank=True, null=True)  # length modified 2022-06-24 to fix 63 char error in prod
    term_own_domain = models.CharField(max_length=127, blank=True, null=True)  # length modified 2022-06-24 to fix 63 char error in prod
    term_type = models.CharField(max_length=15, blank=True, null=True)  # length modified 2022-06-24 to fix 63 char error in prod
    term_group = models.CharField(max_length=127, blank=True, null=True)  # length modified 2022-06-24 to fix 63 char error in prod
    term_site = models.CharField(max_length=45, blank=True, null=True)
    term_territory = models.CharField(max_length=45, blank=True, null=True)
    term_to_uri = models.CharField(max_length=127, blank=True, null=True)  # length modified 2022-06-24 to fix 63 char error in prod
    term_logi_uri = models.CharField(max_length=127, blank=True, null=True)  # length modified 2022-06-24 to fix 63 char error in prod
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
    netsapiens_call_subscription = models.ForeignKey(
        NetsapiensCallSubscription, null=False, on_delete=models.RESTRICT
    )  # update the Serializer.create method if this ever becomes optional
    netsapiens_call_subscription_event_extract = models.ForeignKey(
        NetsapiensCallSubscriptionEventExtract, null=True, on_delete=models.SET_NULL
    )  # most cases, this is what prompted CDR2 acquisitions
    peerlogic_call_id = models.CharField(
        blank=True, default="", max_length=22, db_index=True
    )  # maps to calls/models.py Call model's id (non-fk to keep these segregated)
    peerlogic_call_partial_id = models.CharField(
        blank=True, default="", max_length=22, db_index=True
    )  # maps to calls/models.py CallPartial model's id (non-fk to keep these segregated)
    # These max_lengths are best guesses based on Core1-phx's CdrDomain.201904_r table, unless otherwise specified
    # To be the truest extract we can make without using JSONField, making blank=True for CharFields and null=True for all others
    domain = models.CharField(max_length=63, blank=True, null=True)  # e.g. "pleasantdental-peoria"
    territory = models.CharField(max_length=45, blank=True, null=True)  # e.g. "Peerlogic"
    type = models.IntegerField(max_length=1, null=True)  # e.g. "1", based on CdrDomain.201904_d
    cdr_id = models.CharField(max_length=42, blank=True, null=True)  # e.g."1642816606d99fbc563c6f77ff6ab363a644d87c5b"
    orig_sub = models.CharField(max_length=42, blank=True, null=True)
    orig_from_uri = models.CharField(
        max_length=127, blank=True, null=True
    )  # e.g. "sip:4807984575@67.231.3.4", length modified 2022-06-24 to fix 63 char error in prod
    orig_from_name = models.CharField(max_length=127, blank=True, null=True)  # e.g. "PAULA MALLEY", length modified 2022-06-24 to fix 63 char error in prod
    orig_to_user = models.CharField(max_length=127, blank=True, null=True)  # e.g. "6232952005", length modified 2022-06-24 to fix 63 char error in prod
    orig_req_uri = models.CharField(
        max_length=127, blank=True, null=True
    )  # e.g. "sip:6232952005@core1-phx.peerlogic.com", length modified 2022-06-24 to fix 63 char error in prod
    orig_req_user = models.CharField(max_length=127, blank=True, null=True)  # e.g. "6232952005", length modified 2022-06-24 to fix 63 char error in prod
    by_sub = models.CharField(max_length=127, blank=True, null=True)  # e.g. "4001", length modified 2022-06-24 to fix 63 char error in prod
    term_sub = models.CharField(max_length=63, blank=True, null=True)  # e.g. "1100"
    term_to_uri = models.CharField(max_length=63, blank=True, null=True)  # e.g. "sip:1100@pleasantdental-peoria"
    time_start = models.DateTimeField(null=True)  # e.g. BATCH / OVERALL call start time "1642816606"
    time_answer = models.DateTimeField(null=True)  # e.g. segment / partial "1642816610"
    time_release = models.DateTimeField(null=True)  # e.g. BATCH / OVERALL, call end time "1642816660"
    duration = models.DurationField(null=True)  # e.g. "54" BATCH / OVERALL, should increase with every subsequent partial
    time_talking = models.DurationField(null=True)  # e.g. "54" BATCH / OVERALL, should increase with every subsequent partial
    hide = models.IntegerField(max_length=5, null=True)  # e.g. "0", based on CdrDomain.201904_d
    tag = models.CharField(max_length=45, blank=True, null=True)  # based on CdrDomain.201904_d
    # CDR R values
    cdrr_id = models.CharField(max_length=42, blank=True, null=True)  # overlaps with "id" REDUNDANT: "id": "1642816606d99fbc563c6f77ff6ab363a644d87c5b"
    cdrr_hostname = models.CharField(max_length=32, blank=True, null=True)  # e.g. "core1-phx.peerlogic.com"
    cdrr_mac = models.CharField(max_length=18, blank=True, null=True)  # e.g. "24:6E:96:10:C2:B8"
    cdrr_cdr_index = models.IntegerField(max_length=11, null=True)  # e.g. "1"
    cdrr_orig_callid = models.CharField(max_length=127, blank=True, null=True, db_index=True)  # e.g. "17613391_133144556@67.231.3.4"
    cdrr_orig_ip = models.CharField(max_length=63, blank=True, null=True)  # e.g. "67.231.3.4"
    cdrr_orig_match = models.CharField(max_length=127, blank=True, null=True)  # e.g. "sip*@67.231.3.4"
    cdrr_orig_sub = models.CharField(max_length=42, blank=True, null=True)  # REDUNDANT: "orig_sub": null
    cdrr_orig_domain = models.CharField(max_length=127, blank=True, null=True)  # length modified 2022-06-24 to fix 63 char error in prod
    cdrr_orig_group = models.CharField(max_length=127, blank=True, null=True)  # length modified 2022-06-24 to fix 63 char error in prod
    cdrr_orig_from_uri = models.CharField(
        max_length=127, blank=True, null=True
    )  # REDUNDANT: "orig_from_uri": "sip:4807984575@67.231.3.4", length modified 2022-06-24 to fix 63 char error in prod
    cdrr_orig_from_name = models.CharField(
        max_length=127, blank=True, null=True
    )  # REDUNDANT: "orig_from_name": "PAULA MALLEY", length modified 2022-06-24 to fix 63 char error in prod
    cdrr_orig_from_user = models.CharField(max_length=127, blank=True, null=True)  # e.g. "4807984575", length modified 2022-06-24 to fix 63 char error in prod
    cdrr_orig_from_host = models.CharField(max_length=127, blank=True, null=True)  # e.g. "67.231.3.4", length modified 2022-06-24 to fix 63 char error in prod
    cdrr_orig_req_uri = models.CharField(
        max_length=127, blank=True, null=True
    )  # REDUNDANT: "orig_req_uri": "sip:6232952005@core1-phx.peerlogic.com", length modified 2022-06-24 to fix 63 char error in prod
    cdrr_orig_req_user = models.CharField(
        max_length=127, blank=True, null=True
    )  # REDUNDANT: "orig_req_user": "6232952005", length modified 2022-06-24 to fix 63 char error in prod
    cdrr_orig_req_host = models.CharField(
        max_length=127, blank=True, null=True
    )  # e.g. "core1-phx.peerlogic.com", length modified 2022-06-24 to fix 63 char error in prod
    cdrr_orig_to_uri = models.CharField(
        max_length=127, blank=True, null=True
    )  # e.g. "sip:6232952005@core1-phx.peerlogic.com", length modified 2022-06-24 to fix 63 char error in prod
    cdrr_orig_to_user = models.CharField(
        max_length=127, blank=True, null=True
    )  # REDUNDANT: "orig_to_user": "6232952005", length modified 2022-06-24 to fix 63 char error in prod
    cdrr_orig_to_host = models.CharField(
        max_length=127, blank=True, null=True
    )  # e.g. "core1-phx.peerlogic.com", length modified 2022-06-24 to fix 63 char error in prod
    cdrr_by_action = models.CharField(max_length=31, blank=True, null=True)  # e.g. "QueueSDispatch"
    cdrr_by_sub = models.CharField(max_length=63, blank=True, null=True)  # REDUNDANT: "by_sub": "4001"
    cdrr_by_domain = models.CharField(max_length=63, blank=True, null=True)  # e.g. "pleasantdental-peoria"
    cdrr_by_group = models.CharField(max_length=63, blank=True, null=True)  # e.g. "Front Office"
    cdrr_by_uri = models.CharField(max_length=63, blank=True, null=True)
    cdrr_by_callid = models.CharField(max_length=127, blank=True, null=True, db_index=True)  # e.g. "20220122015646001363-8d8a5d555a2bdaa84182cb8f8d613b03"
    cdrr_term_callid = models.CharField(max_length=127, blank=True, null=True, db_index=True)  # e.g. "20220122015647001366-8d8a5d555a2bdaa84182cb8f8d613b03"
    cdrr_term_ip = models.CharField(max_length=63, blank=True, null=True)  # e.g. "98.174.249.67"
    cdrr_term_match = models.CharField(max_length=127, blank=True, null=True)  # e.g. "sip:1100@pleasantdental-peoria"
    cdrr_term_sub = models.CharField(
        max_length=127, blank=True, null=True
    )  # REDUNDANT: "term_sub": "1100", length modified 2022-06-24 to fix 63 char error in prod
    cdrr_term_domain = models.CharField(
        max_length=127, blank=True, null=True
    )  # e.g. "pleasantdental-peoria", length modified 2022-06-24 to fix 63 char error in prod
    cdrr_term_to_uri = models.CharField(
        max_length=127, blank=True, null=True
    )  # REDUNDANT: "term_to_uri": "sip:1100@pleasantdental-peoria", length modified 2022-06-24 to fix 63 char error in prod
    cdrr_term_group = models.CharField(max_length=127, blank=True, null=True)  # e.g. "Front Office", length modified 2022-06-24 to fix 63 char error in prod
    cdrr_time_start = models.DateTimeField(null=True)  # "time_start": "1642816607" of this segment / partial
    cdrr_time_ringing = models.DateTimeField(null=True)  # e.g. "1642816607"
    cdrr_time_answer = models.DateTimeField(null=True)  # REDUNDANT: "time_answer": "1642816610"
    cdrr_time_release = models.DateTimeField(null=True)  # REDUNDANT: "time_release": "1642816660"
    cdrr_time_talking = models.DurationField(null=True)  # "time_talking": "50" for this segment / partial
    cdrr_time_holding = models.DurationField(null=True)  # e.g. "0"  Time holding on this segment
    cdrr_duration = models.DurationField(null=True)  # e.g. "50" for this segment / partial
    cdrr_time_insert = models.DateTimeField(null=True)  # e.g.
    cdrr_time_disp = models.DateTimeField(null=True)  # e.g.
    cdrr_release_code = models.CharField(max_length=15, blank=True, null=True)  # e.g. "end"
    cdrr_release_text = models.CharField(max_length=63, blank=True, null=True, db_index=True)  # e.g. "Orig: Bye"
    cdrr_codec = models.CharField(max_length=15, blank=True, null=True)  # e.g. "PCMU"
    cdrr_rly_prt_0 = models.CharField(max_length=15, blank=True, null=True)  # e.g. "26120"
    cdrr_rly_prt_a = models.CharField(max_length=31, blank=True, null=True)  # e.g. "98.174.249.67:11796"
    cdrr_rly_prt_b = models.CharField(max_length=31, blank=True, null=True)  # e.g. "67.231.0.123:15772"
    cdrr_rly_cnt_a = models.CharField(max_length=15, blank=True, null=True)  # e.g. "424668"
    cdrr_rly_cnt_b = models.CharField(max_length=15, blank=True, null=True)  # e.g. "425700"
    cdrr_image_codec = models.CharField(max_length=15, blank=True, null=True)
    cdrr_image_prt_0 = models.CharField(max_length=31, blank=True, null=True)
    cdrr_image_prt_a = models.CharField(max_length=31, blank=True, null=True)
    cdrr_image_prt_b = models.CharField(max_length=31, blank=True, null=True)
    cdrr_image_cnt_a = models.CharField(max_length=15, blank=True, null=True)
    cdrr_image_cnt_b = models.CharField(max_length=15, blank=True, null=True)
    cdrr_video_codec = models.CharField(max_length=15, blank=True, null=True)
    cdrr_video_prt_0 = models.CharField(max_length=15, blank=True, null=True)
    cdrr_video_prt_a = models.CharField(max_length=31, blank=True, null=True)
    cdrr_video_prt_b = models.CharField(max_length=31, blank=True, null=True)
    cdrr_video_cnt_a = models.CharField(max_length=15, blank=True, null=True)
    cdrr_video_cnt_b = models.CharField(max_length=15, blank=True, null=True)
    cdrr_disp_type = models.CharField(max_length=32, blank=True, null=True)
    cdrr_disposition = models.CharField(max_length=15, blank=True, null=True)
    cdrr_reason = models.CharField(max_length=64, blank=True, null=True)
    cdrr_notes = models.TextField(blank=True, null=True)
    cdrr_pac = models.CharField(max_length=31, blank=True, null=True)
    cdrr_orig_logi_uri = models.CharField(
        max_length=127, blank=True, null=True
    )  # e.g. "sip:4807984575@67.231.3.4", length modified 2022-06-24 to fix 63 char error in prod
    cdrr_term_logi_uri = models.CharField(
        max_length=127, blank=True, null=True
    )  # e.g. "sip:16232952005@pleasantdental-peoria", length modified 2022-06-24 to fix 63 char error in prod
    cdrr_batch_tim_beg = models.IntegerField(max_length=16, null=True)  # e.g. "1642816606"  The same across all cdr partials for a call, matches time_start
    cdrr_batch_tim_ans = models.IntegerField(max_length=16, null=True)  # e.g. "1642816606"  The same across all cdr partials for a call, matches time_start?
    cdrr_batch_hold = models.IntegerField(max_length=15, null=True)  # e.g. "0"  Aggregate hold time so far
    cdrr_batch_dura = models.IntegerField(max_length=15, null=True)  # e.g. "54"  Matches the duration at root
    cdrr_orig_id = models.CharField(max_length=127, blank=True, null=True)  # e.g. "4807984575", length modified 2022-06-24 to fix 63 char error in prod
    cdrr_term_id = models.CharField(max_length=127, blank=True, null=True)  # e.g. "6232952005", length modified 2022-06-24 to fix 63 char error in prod
    cdrr_by_id = models.CharField(max_length=127, blank=True, null=True)  # e.g. "6232952005", length modified 2022-06-24 to fix 63 char error in prod
    cdrr_route_to = models.CharField(max_length=255, blank=True, null=True)  # e.g. "sip:*@*"
    cdrr_route_class = models.CharField(max_length=15, blank=True, null=True)  # e.g. "0"
    cdrr_orig_territory = models.CharField(max_length=45, blank=True, null=True)
    cdrr_orig_site = models.CharField(max_length=45, blank=True, null=True)
    cdrr_by_site = models.CharField(max_length=45, blank=True, null=True)
    cdrr_by_territory = models.CharField(max_length=45, blank=True, null=True)  # e.g. "Peerlogic"
    cdrr_term_territory = models.CharField(max_length=45, blank=True, null=True)  # e.g. "Peerlogic"
    cdrr_term_site = models.CharField(max_length=45, blank=True, null=True)

    def calculate_connected_or_missed_call(self) -> str:
        """Determine if the call connected / was answered or was ultimately missed. We MIGHT only know this based upon the last cdr in the batch."""
        if self.type == 2:
            return "missed"
        return "connected"

    def went_to_voicemail(self) -> bool:
        """Whether the call ended at the voicemail box to record a voicemail."""
        return self.cdrr_term_to_uri.lower() == "vmail"
