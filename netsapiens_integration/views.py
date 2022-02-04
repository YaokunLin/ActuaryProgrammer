import logging
from typing import List

from django.conf import settings
from django.core import serializers
from django.shortcuts import get_object_or_404
from google.api_core.exceptions import PermissionDenied
from rest_framework import status, viewsets
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import (
    AllowAny,
    IsAdminUser,
)
from rest_framework.response import Response

from core.models import PracticeTelecom
from netsapiens_integration.helpers import get_callid_tuples_from_subscription_event
from netsapiens_integration.publishers import publish_leg_b_ready_cdrs

from .models import (
    NetsapiensAPICredentials,
    NetsapiensCallSubscriptions,
    NetsapiensCallSubscriptionsEventExtract,
    NetsapiensCdr2Extract,
)
from .serializers import (
    AdminNetsapiensAPICredentialsSerializer,
    NetsapiensAPICredentialsReadSerializer,
    NetsapiensAPICredentialsWriteSerializer,
    NetsapiensCallSubscriptionsEventExtractSerializer,
    NetsapiensCallSubscriptionsSerializer,
    NetsapiensCdr2ExtractSerializer,
)

# Get an instance of a logger
log = logging.getLogger(__name__)

# Headers:
# {
# 	'Host': 'peerlogic-api-dev.wn.r.appspot.com',
# 	'X-Forwarded-For': '216.223.176.51, 169.254.1.1',
# 	'X-Forwarded-Proto': 'https',
# 	'Forwarded': 'for="216.223.176.51";proto=https',
# 	'Content-Length': '2212',
# 	'Content-Type': 'application/json',
# 	'X-Cloud-Trace-Context': 'a22b744cbbbb520500e7b9ace7879adf/7072971351974001544',
# 	'X-Appengine-Country': 'US',
# 	'X-Appengine-City': 'dallas',
# 	'X-Appengine-Citylatlong': '32.776664,-96.796988',
# 	'X-Appengine-Region': 'tx',
# 	'Traceparent': '00-a22b744cbbbb520500e7b9ace7879adf-62283df86cecbb88-00',
# 	'X-Appengine-Timeout-Ms': '599999',
# 	'X-Appengine-Https': 'on',
# 	'X-Appengine-User-Ip': '216.223.176.51',
# 	'X-Appengine-Api-Ticket': 'ChBhNjAzYjAwYTViMzFhNDA1EKHVnxUQqNWfFRoTCJ3645DMvPUCFWTG/AodIXoB+Q==',
# 	'X-Appengine-Request-Log-Id': '61e7601900ff0384dd9cd6f52c00017a776e7e706565726c6f6769632d6170692d6465760001323032323031313974303034353432000100',
# 	'X-Appengine-Default-Version-Hostname': 'peerlogic-api-dev.wn.r.appspot.com'
# }
# Data
# [{
# 	'hostname': 'core1-phx.peerlogic.com',
# 	'sessionId': '20220119004825004744',
# 	'orig_callid': '0_1063160652@192.168.168.127',
# 	'orig_leg_tag': 'Om7pAVCOHJLGixtIA1FA2E',
# 	'orig_ip': '98.174.249.67',
# 	'orig_match': 'sip:1110@pleasantdental-peoria',
# 	'orig_sub': '1110',
# 	'orig_domain': 'pleasantdental-peoria',
# 	'orig_own_sub': '1110',
# 	'orig_own_domain': 'pleasantdental-peoria',
# 	'orig_type': 'device',
# 	'orig_group': 'Front Office',
# 	'orig_site': '',
# 	'orig_territory': 'Peerlogic',
# 	'orig_from_uri': 'sip:6232952005@pleasantdental-peoria',
# 	'orig_logi_uri': 'sip:1110@pleasantdental-peoria',
# 	'orig_from_name': 'Front Office 2',
# 	'orig_from_user': '6232952005',
# 	'orig_from_host': 'pleasantdental-peoria',
# 	'orig_req_uri': 'sip:6616077417@pleasantdental-peoria.core1-phx.peerlogic.com',
# 	'orig_req_user': '6616077417',
# 	'orig_req_host': 'pleasantdental-peoria.core1-phx.peerlogic.com',
# 	'orig_to_uri': 'sip:6616077417@pleasantdental-peoria.core1-phx.peerlogic.com',
# 	'orig_to_user': '6616077417',
# 	'orig_to_host': 'pleasantdental-peoria.core1-phx.peerlogic.com',
# 	'by_action': '',
# 	'by_sub': '',
# 	'by_domain': '',
# 	'by_type': '',
# 	'by_group': '',
# 	'by_site': '',
# 	'by_territory': '',
# 	'by_uri': '',
# 	'by_callid': '',
# 	'term_callid': '20220119004825004745-8d8a5d555a2bdaa84182cb8f8d613b03',
# 	'term_leg_tag': 'Vmhj3zA8Wjm31vbNA1FA2F',
# 	'term_ip': '67.231.4.70',
# 	'term_match': 'sip:*@67.231.4.70',
# 	'term_sub': '',
# 	'term_domain': '*',
# 	'term_own_sub': '',
# 	'term_own_domain': '*',
# 	'term_type': 'gateway',
# 	'term_group': '',
# 	'term_site': '',
# 	'term_territory': '',
# 	'term_to_uri': 'sip:16616077417@67.231.4.70',
# 	'term_logi_uri': 'sip:16616077417@pleasantdental-peoria',
# 	'time_start': '2022-01-19 00:48:25',
# 	'time_answer': '2022-01-19 00:48:59',
# 	'orig_id': '6232952005',
# 	'term_id': '16616077417',
# 	'by_id': '',
# 	'orig_call_info': 'active',
# 	'term_call_info': 'active',
# 	'route_to': 'sip:1??????????@*',
# 	'route_class': '0',
# 	'media': 'PCMU',
# 	'pac': '',
# 	'action': 'nop',
# 	'action_parameter': '',
# 	'action_by': '',
# 	'notes': '',
# 	'time_refresh': '2022-01-19 00:48:59',
# 	'ts': '2022-01-19 00:48:59',
# 	'term_uri': 'sip:16616077417@67.231.4.70',
# 	'dnis': '6616077417',
# 	'orig_name': 'Front Office 2',
# 	'ani': '6232952005',
# 	'orig_user': '1110',
# 	'term_user': '',
# 	'time_begin': '2022-01-19 00:48:25',
# 	'acr_id': '0_1063160652@192.168.168.127_20220119004825004745-8d8a5d555a2bdaa84182cb8f8d613b03_16616077417',
# 	'remove': 'yes'
# }]
@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def netsapiens_call_subscription_event_receiver_view(request, practice_telecom_id=None, call_subscription_id=None):
    log.info(
        f"Netsapiens Call subscription: Headers: '{request.headers}' POST Data '{request.data}' practice_telecom_id: '{practice_telecom_id}' and call_subscription_id: '{call_subscription_id}'"
    )

    #
    # Enabled
    #

    # Check if this is enabled first
    log.info(
        f"Determining if Call Subscription Event Processing is enabled before processing event for: practice_telecom_id: '{practice_telecom_id}' and call_subscription_id: '{call_subscription_id}'"
    )
    if settings.NETSAPIENS_INTEGRATION_CALL_MODEL_SUBSCRIPTION_IS_ENABLED:
        message = f"Call Subscription Event processing is disabled on this system. If you believe this was in error, please contact peerlogic for assistance."
        log.info(
            f"NETSAPIENS_INTEGRATION_CALL_MODEL_SUBSCRIPTION_IS_ENABLED is false. Not saving event POST Data '{request.data}' practice_telecom_id: '{practice_telecom_id}' and call_subscription_id: '{call_subscription_id}'"
        )
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED, data={"message": message})
    log.info(
        f"Call Subscription Event Processing is enabled. Processing to process event for: practice_telecom_id: '{practice_telecom_id}' and call_subscription_id: '{call_subscription_id}'"
    )

    #
    # VALIDATION
    #

    log.info(
        f"Validating practice telecom, practice, voip_provider, and call_subscription for: practice_telecom_id: '{practice_telecom_id}' and call_subscription_id: '{call_subscription_id}'"
    )

    # validate practice telecom exists and is active
    practice_telecom: PracticeTelecom = get_object_or_404(
        PracticeTelecom.objects.select_related("practice", "voip_provider"), pk=practice_telecom_id, practice__active=True
    )

    # validate an active subscription exists and is associated with the practice telecom, not referenced later, we just need the check
    get_object_or_404(NetsapiensCallSubscriptions, pk=call_subscription_id, active=True)

    # Grab Practice and VOIP Provider for downstream processing
    practice = practice_telecom.practice
    practice_id = practice_telecom.practice.id

    if not practice:
        message = f"No valid practice found for practice_telecom_id = '{practice_telecom_id}'"
        log.exception(f"{message}. This should not be possible since this is a non-nullable relationship.")
        return Response(status=status.HTTP_404_NOT_FOUND, data={"message": message})

    voip_provider = practice_telecom.voip_provider
    if not voip_provider:
        message = (
            f"No valid voip_provider found for this practice '{practice_id}'. A voip_provider must be set up first in order to receive subscription events."
        )
        log.exception(f"{message}. Practice is not set up properly and needs a voip_provider. Somehow a subscription was set up and events are being received!")
        return Response(status=status.HTTP_404_NOT_FOUND, data={"message": message})
    voip_provider_id = voip_provider.id

    # Validate subscription payload by converting to NetsapiensCallSubscriptionsEventExtract
    log.info(f"Validating subscription payload for : practice_telecom_id: '{practice_telecom_id}' and call_subscription_id: '{call_subscription_id}'")
    event_data = request.data

    # add the call-subscription-id for now since we don't want these orphaned
    # TODO: find a better way to not pollute the raw events with our ids and to not duplicate this contract in the data payload and event attributes below
    for event in event_data:
        event["netsapiens_call_subscription_id"] = call_subscription_id

    callid_orig_by_term_pairings_list = get_callid_tuples_from_subscription_event(event_data)
    subscription_event_serializer = NetsapiensCallSubscriptionsEventExtractSerializer(data=event_data, many=True)
    subscription_event_serializer_is_valid = subscription_event_serializer.is_valid()
    if not subscription_event_serializer_is_valid:
        log.exception(
            f"Error from subscription_event_serializer validation from callids {callid_orig_by_term_pairings_list}: {subscription_event_serializer.errors}"
        )
        return Response(status=status.HTTP_400_BAD_REQUEST, data={"errors": subscription_event_serializer.errors})

    # save events
    saved_event_data: List[NetsapiensCallSubscriptionsEventExtract] = subscription_event_serializer.save()

    # convert events into something that's emitable as a dictionary
    saved_event_data = subscription_event_serializer.to_representation(saved_event_data)
    for event in saved_event_data:
        event["netsapiens_call_subscription_event_extract_id"] = event.pop("id")

    log.info(
        f"Extracted data for call ids: {callid_orig_by_term_pairings_list} from: practice_telecom_id: '{practice_telecom_id}' and call_subscription_id: '{call_subscription_id}'"
    )

    #
    # PROCESSING
    #

    try:
        log.info(f"Publishing leg b ready events for: practice_telecom_id: '{practice_telecom_id}' and call_subscription_id: '{call_subscription_id}'")
        publish_leg_b_ready_cdrs(
            netsapiens_call_subscription_id=call_subscription_id, practice_id=practice_id, voip_provider_id=voip_provider_id, event_data=saved_event_data
        )
        log.info(f"Published leg b ready events for: practice_telecom_id: '{practice_telecom_id}' and call_subscription_id: '{call_subscription_id}'")
    except PermissionDenied:
        message = "Must add role 'roles/pubsub.publisher'. Exiting."
        log.exception(message)
        return Response(status=status.HTTP_403_FORBIDDEN, data={"error": message})

    # publish_futures = publish_leg_b_ready_cdrs(event_data)
    # Experimenting with NOT waiting for all the publish futures to resolve before responding.
    # futures.wait(publish_futures, return_when=futures.ALL_COMPLETED)

    return Response(status=status.HTTP_202_ACCEPTED, data=event_data)


# Headers:
# {
# 	'Host': 'peerlogic-api-dev.wn.r.appspot.com',
# 	'X-Forwarded-For': '216.223.176.51, 169.254.1.1',
# 	'X-Forwarded-Proto': 'https',
# 	'Forwarded': 'for="216.223.176.51";proto=https',
# 	'Content-Length': '465',
# 	'Content-Type': 'application/json',
# 	'X-Cloud-Trace-Context': 'ad1e0ddce585b6aadf9b55bee993dd1c/14144572817051253132',
# 	'X-Appengine-City': 'dallas',
# 	'X-Appengine-Region': 'tx',
# 	'X-Appengine-Country': 'US',
# 	'X-Appengine-Citylatlong': '32.776664,-96.796988',
# 	'Traceparent': '00-ad1e0ddce585b6aadf9b55bee993dd1c-c44b9e0933fc798c-00',
# 	'X-Appengine-Timeout-Ms': '599999',
# 	'X-Appengine-Https': 'on',
# 	'X-Appengine-User-Ip': '216.223.176.51',
# 	'X-Appengine-Api-Ticket': 'ChAxODE3OTM2YTNlMjk2MDQ5EKHVnxUQqNWfFRoTCNHu45DMvPUCFWvG/AoduswB5w==',
# 	'X-Appengine-Request-Log-Id': '61e7601900ff037f11b10402c700017a776e7e706565726c6f6769632d6170692d6465760001323032323031313974303034353432000100',
# 	'X-Appengine-Default-Version-Hostname': 'peerlogic-api-dev.wn.r.appspot.com'
# }

# POST Data:
# [{
# 	'orig_callid': '0_1063160652@192.168.168.127',
# 	'orig_from_uri': 'sip:6232952005@pleasantdental-peoria',
# 	'orig_from_name': 'Front Office 2',
# 	'orig_to_user': '6616077417',
# 	'orig_user': '1110',
# 	'orig_domain': 'pleasantdental-peoria',
# 	'by_user': '',
# 	'by_domain': '',
# 	'term_user': '',
# 	'term_domain': '*',
# 	'term_to_uri': 'sip:16616077417@67.231.4.70',
# 	'orig_call_info': 'active',
# 	'term_call_info': 'active',
# 	'time_answer': '2022-01-19 00:48:59',
# 	'time_start': '2022-01-19 00:48:25',
# 	'remove': 'yes'
# }]
@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def netsapiens_call_origid_subscription_event_receiver_view(request):
    log.info(f"Netsapiens Call ORIG id subscription: Headers: {request.headers} POST Data {request.data}")
    callid_orig_by_term_pairings_list = get_callid_tuples_from_subscription_event(request.data)
    if settings.NETSAPIENS_INTEGRATION_CALL_ORIGID_MODEL_SUBSCRIPTION_IS_ENABLED:
        # NetsapiensCallOrigIdSubscriptionEventExtract creation
        log.info(f"Extract data for call ids: {callid_orig_by_term_pairings_list} from Call ORIG id subscription saved to netsapiens etl cdrs extract.")
    else:
        log.info(
            f"NETSAPIENS_INTEGRATION_CALL_ORIGID_MODEL_SUBSCRIPTION_IS_ENABLED is false. Not saving to database for call ids {callid_orig_by_term_pairings_list}"
        )

    return Response(request.data)


class NetsapiensAPICredentialsViewset(viewsets.ModelViewSet):
    queryset = NetsapiensAPICredentials.objects.all().order_by("voip_provider", "active", "-created_at")
    filterset_fields = ["voip_provider", "active"]

    serializer_class_read = NetsapiensAPICredentialsReadSerializer
    serializer_class_write = NetsapiensAPICredentialsWriteSerializer

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return self.serializer_class_write

        return self.serializer_class_read


class AdminNetsapiensAPICredentialsViewset(viewsets.ModelViewSet):
    queryset = NetsapiensAPICredentials.objects.all().order_by("voip_provider", "active", "-created_at")
    serializer_class = AdminNetsapiensAPICredentialsSerializer
    permission_classes = [IsAdminUser]

    filterset_fields = ["voip_provider", "active"]


class NetsapiensCallSubscriptionsViewset(viewsets.ModelViewSet):
    queryset = NetsapiensCallSubscriptions.objects.all().order_by("-modified_at")
    serializer_class = NetsapiensCallSubscriptionsSerializer

    filterset_fields = ["practice_telecom"]


class NetsapiensCallSubscriptionsEventExtractViewset(viewsets.ModelViewSet):
    queryset = NetsapiensCallSubscriptionsEventExtract.objects.all()
    serializer_class = NetsapiensCallSubscriptionsEventExtractSerializer

    filterset_fields = ["orig_callid", "by_callid", "term_callid"]


class NetsapiensCdr2ExtractViewset(viewsets.ModelViewSet):
    queryset = NetsapiensCdr2Extract.objects.all()
    serializer_class = NetsapiensCdr2ExtractSerializer

    filterset_fields = ["orig_callid", "by_callid", "term_callid"]
