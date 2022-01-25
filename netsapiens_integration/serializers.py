from rest_framework import serializers

from .models import (
    NetsapiensAPICredentials,
    NetsapiensCallsSubscriptionEventExtract,
    NetsapiensSubscriptionClient,
)


class NetsapiensCallsSubscriptionEventExtractSerializer(serializers.ModelSerializer):
    class Meta:
        model = NetsapiensCallsSubscriptionEventExtract
        fields = "__all__"


class NetsapiensCallSubscriptionPayloadSerializer(serializers.Serializer):
    hostname = serializers.CharField()  # core1-phx.peerlogic.com
    sessionId = serializers.CharField()  # 20220119004825004744
    orig_callid = serializers.CharField()  # 0_1063160652@192.168.168.127
    orig_leg_tag = serializers.CharField()  # Om7pAVCOHJLGixtIA1FA2E
    orig_ip = serializers.CharField()  # 98.174.249.67
    orig_match = serializers.CharField()  # sip:1110@pleasantdental-peoria
    orig_sub = serializers.CharField()  # 1110
    orig_domain = serializers.CharField()  # pleasantdental-peoria
    orig_own_sub = serializers.CharField()  # 1110
    orig_own_domain = serializers.CharField()  # pleasantdental-peoria
    orig_type = serializers.CharField()  # device
    orig_group = serializers.CharField()  # Front Office
    orig_site = serializers.CharField()  #
    orig_territory = serializers.CharField()  # Peerlogic
    orig_from_uri = serializers.CharField()  # sip:6232952005@pleasantdental-peoria
    orig_logi_uri = serializers.CharField()  # sip:1110@pleasantdental-peoria
    orig_from_name = serializers.CharField()  # Front Office 2
    orig_from_user = serializers.CharField()  # 6232952005
    orig_from_host = serializers.CharField()  # pleasantdental-peoria
    orig_req_uri = serializers.CharField()  # sip:6616077417@pleasantdental-peoria.core1-phx.peerlogic.com
    orig_req_user = serializers.CharField()  # 6616077417
    orig_req_host = serializers.CharField()  # pleasantdental-peoria.core1-phx.peerlogic.com
    orig_to_uri = serializers.CharField()  # sip:6616077417@pleasantdental-peoria.core1-phx.peerlogic.com
    orig_to_user = serializers.CharField()  # 6616077417
    orig_to_host = serializers.CharField()  # pleasantdental-peoria.core1-phx.peerlogic.com
    by_action = serializers.CharField()
    by_sub = serializers.CharField()
    by_domain = serializers.CharField()
    by_type = serializers.CharField()
    by_group = serializers.CharField()
    by_site = serializers.CharField()
    by_territory = serializers.CharField()
    by_uri = serializers.CharField()
    by_callid = serializers.CharField()
    term_callid = serializers.CharField()  # 20220119004825004745-8d8a5d555a2bdaa84182cb8f8d613b03
    term_leg_tag = serializers.CharField()  # Vmhj3zA8Wjm31vbNA1FA2F
    term_ip = serializers.CharField()  # 67.231.4.70
    term_match = serializers.CharField()  # sip =*@67.231.4.70
    term_sub = serializers.CharField()  #
    term_domain = serializers.CharField()  # *
    term_own_sub = serializers.CharField()
    term_own_domain = serializers.CharField()  # *
    term_type = serializers.CharField()  # gateway
    term_group = serializers.CharField()  #
    term_site = serializers.CharField()  #
    term_territory = serializers.CharField()  #
    term_to_uri = serializers.CharField()  # sip =16616077417@67.231.4.70
    term_logi_uri = serializers.CharField()  # sip:16616077417@pleasantdental-peoria
    time_start = serializers.CharField()  # 2022-01-19 00:48:25
    time_answer = serializers.CharField()  # 2022-01-19 00:48:59
    orig_id = serializers.CharField()  # 6232952005
    term_id = serializers.CharField()  # 16616077417
    by_id = serializers.CharField()
    orig_call_info = serializers.CharField()  # active
    term_call_info = serializers.CharField()  # active
    route_to = serializers.CharField()  # sip =1??????????@*
    route_class = serializers.CharField()  # 0
    media = serializers.CharField()  # PCMU
    pac = serializers.CharField()
    action = serializers.CharField()  # nop
    action_parameter = serializers.CharField()
    action_by = serializers.CharField()
    notes = serializers.CharField()
    time_refresh = serializers.CharField()  # 2022-01-19 00 =48 =59
    ts = serializers.CharField()  # 2022-01-19 00 =48 =59
    term_uri = serializers.CharField()  # sip =16616077417@67.231.4.70
    dnis = serializers.CharField()  # 6616077417
    orig_name = serializers.CharField()  # Front Office 2
    ani = serializers.CharField()  # 6232952005
    orig_user = serializers.CharField()  # 1110
    term_user = serializers.CharField()  #
    time_begin = serializers.CharField()  # 2022-01-19 00:48:25
    acr_id = serializers.CharField()  # 0_1063160652@192.168.168.127_20220119004825004745-8d8a5d555a2bdaa84182cb8f8d613b03_16616077417
    remove = serializers.CharField(allow_null=True)  # yes


class NetsapiensAPICredentialsReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = NetsapiensAPICredentials
        read_only_fields = ["id", "created_at", "modified_by", "modified_at"]
        fields = ["id", "created_at", "modified_by", "modified_at", "voip_provider", "authentication_url", "call_subscription_url", "client_id", "username"]


class NetsapiensAPICredentialsWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = NetsapiensAPICredentials
        read_only_fields = ["id", "created_at", "modified_by", "modified_at"]
        fields = ["id", "created_at", "modified_by", "modified_at", "voip_provider", "authentication_url", "call_subscription_url", "client_id", "client_secret", "username", "password"]


class NetsapiensSubscriptionClientSerializer(serializers.ModelSerializer):
    call_subscription_uri = serializers.CharField()

    class Meta:
        model = NetsapiensSubscriptionClient
        read_only_fields = ["id", "created_at", "modified_by", "modified_at"]
        fields = ["id", "created_at", "modified_by", "modified_at", "voip_provider", "call_subscription_uri"]
