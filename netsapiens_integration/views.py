import logging

from django.conf import settings
from rest_framework import status, viewsets
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from netsapiens_integration.helpers import get_callid_tuples_from_subscription_event

from .models import NetsapiensSubscriptionClient
from .serializers import NetsapiensCallsSubscriptionEventExtractSerializer, NetsapiensSubscriptionClientSerializer

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
def netsapiens_call_subscription_view(request, voip_provider_id=None, client_id=None):
    log.info(f"VOIP provider id: {voip_provider_id}")
    log.info(f"VOIP NetsapiensSubscriptionClient id: {client_id}")
    client = NetsapiensSubscriptionClient.objects.get(pk=client_id)
    if client.voip_provider.id != voip_provider_id:
        return Response(status=status.HTTP_400_BAD_REQUEST, data={"errors": "Invalid VOIP Provider."})

    log.info(f"Netsapiens Call subscription: Headers: {request.headers} POST Data {request.data}")
    event_data = request.data
    for cdr in event_data:
        cdr["netsapiens_subscription_client"] = client_id
    callid_orig_by_term_pairings_list = get_callid_tuples_from_subscription_event(event_data)
    if settings.NETSAPIENS_ETL_CALL_MODEL_SUBSCRIPTION_TYPE == "call":
        # Convert subscription payload to NetsapiensCallsSubscriptionEventExtract
        subscription_event_serializer = NetsapiensCallsSubscriptionEventExtractSerializer(data=request.data, many=True)
        subscription_event_serializer_is_valid = subscription_event_serializer.is_valid()
        if not subscription_event_serializer_is_valid:
            log.exception(
                f"Error from subscription_event_serializer validation from callids {callid_orig_by_term_pairings_list}: {subscription_event_serializer.errors}"
            )
            return Response(status=status.HTTP_400_BAD_REQUEST, data={"errors": subscription_event_serializer.errors})

        subscription_events = subscription_event_serializer.save()
        log.info(f"Extract data for call ids: {callid_orig_by_term_pairings_list} from Call subscription saved to netsapiens etl cdrs extract.")
    else:
        log.info(f"NETSAPIENS_ETL_CALL_MODEL_SUBSCRIPTION_TYPE not set to call. Not saving to database for call ids {callid_orig_by_term_pairings_list}")
    return Response(request.data)


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
def netsapiens_call_origid_subscription_view(request):
    log.info(f"Netsapiens Call ORIG id subscription: Headers: {request.headers} POST Data {request.data}")
    callid_orig_by_term_pairings_list = get_callid_tuples_from_subscription_event(request.data)
    if settings.NETSAPIENS_ETL_CALL_MODEL_SUBSCRIPTION_TYPE == "call_origid":
        # NetsapiensCallOrigIdSubscriptionEventExtract creation
        log.info(f"Extract data for call ids: {callid_orig_by_term_pairings_list} from Call ORIG id subscription saved to netsapiens etl cdrs extract.")
    else:
        log.info(f"NETSAPIENS_ETL_CALL_MODEL_SUBSCRIPTION_TYPE not set to call_origid. Not saving to database for call ids {callid_orig_by_term_pairings_list}")

    return Response(request.data)


class NetsapiensSubscriptionClientViewset(viewsets.ModelViewSet):
    queryset = NetsapiensSubscriptionClient.objects.all().order_by("-modified_at")
    serializer_class = NetsapiensSubscriptionClientSerializer

    filterset_fields = ["voip_provider"]
