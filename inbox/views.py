from django.conf import settings
from django.http import Http404

from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .bandwidth.serializers import (
    BandwidthResponseToSMSMessageSerializer,
    CreateSMSMessageAndConvertToBandwidthRequestSerializer,
    MessageDeliveredEventSerializer,
    MessageFailedEventSerializer,
)
from .models import SMSMessage
from .serializers import SMSMessageSerializer


class SMSMessageViewSet(viewsets.ModelViewSet):
    queryset = SMSMessage.objects.all().order_by("-created_at")
    serializer_class = SMSMessageSerializer


class SMSMessagesDeliveredCallbackView(APIView):
    """Callback from Bandwidth letting us know the message was delivered"""

    def post(self, request, format=None):
        bandwidth_ids = [item["message"]["id"] for item in request.data]

        # Get the existing database records
        sms_message = SMSMessage.objects.filter(bandwidth_id__in=bandwidth_ids).first()

        # Check inputs
        # IMPORTANT NOTE ABOUT MMS AND GROUP MESSAGES!
        # MMS and Group messages do currently support delivery receipts.
        # However, you will need to have this enabled. Without the delivery receipts enabled,
        # you will still receive a message delivered event when the message is sent.
        # The message delivered event will not represent true delivery for only MMS and Group Messages.
        # This will mean your message has been handed off to the Bandwidth's MMSC network,
        # but has not been confirmed at the downstream carrier.
        # https://dev.bandwidth.com/messaging/callbacks/msgDelivered.html
        message_delivered_event_serializer = MessageDeliveredEventSerializer(sms_message, data=request.data[0])
        message_delivered_event_serializer_is_valid = message_delivered_event_serializer.is_valid()
        if not message_delivered_event_serializer_is_valid:
            return Response(message_delivered_event_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Update the record in the database
        message_delivered_event_serializer.save()

        # Response serializer is a normal sms_message serializer
        sms_message.refresh_from_db()
        serializer = SMSMessageSerializer(sms_message)

        return Response(serializer.data, status=status.HTTP_202_ACCEPTED)


class SMSMessagesFailedCallbackView(APIView):
    """Callback from Bandwidth letting us know the message failed to be delivered"""

    def post(self, request, format=None):
        bandwidth_ids = [item["message"]["id"] for item in request.data]

        # Get the existing database records
        sms_message = SMSMessage.objects.filter(bandwidth_id__in=bandwidth_ids).first()

        # Check inputs
        # In order to receive message events, you need to ensure you have set up your application to send
        # callbacks to your server's URL.
        # For MMS and Group Messages, you will only receive this callback if you have enabled
        # delivery receipts on MMS.
        message_delivered_event_serializer = MessageFailedEventSerializer(sms_message, data=request.data[0])
        message_delivered_event_serializer_is_valid = message_delivered_event_serializer.is_valid()
        if not message_delivered_event_serializer_is_valid:
            return Response(message_delivered_event_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Update the record in the database
        message_delivered_event_serializer.save()

        # Response serializer is a normal sms_message serializer
        sms_message.refresh_from_db()
        serializer = SMSMessageSerializer(sms_message)

        return Response(serializer.data, status=status.HTTP_202_ACCEPTED)


class SMSMessagesView(APIView):
    """
    Create a new SMSMessage.
    # TODO: list once Bandwidth callbacks are available
    # TODO: from_number will always come from 1 assigned group/domain's sms number, not willy-nilly
    """

    def post(self, request, format=None):
        # Check inputs
        create_message_serializer = CreateSMSMessageAndConvertToBandwidthRequestSerializer(data=request.data)
        create_message_serializer_is_valid = create_message_serializer.is_valid()
        if not create_message_serializer_is_valid:
            return Response(create_message_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Call Telecom Client
        response = settings.BANDWIDTH_CLIENT.post(settings.BANDWIDTH_MESSAGING_URI, json=create_message_serializer.data)
        response_data = response.json()

        if response.status_code >= 300:
            return Response(response_data, status=response.status_code)

        # Convert Response to sms message
        bandwidth_response_to_sms_message = BandwidthResponseToSMSMessageSerializer(data=response_data)
        bandwidth_response_to_sms_message_is_valid = bandwidth_response_to_sms_message.is_valid()
        if not bandwidth_response_to_sms_message_is_valid:
            return Response(bandwidth_response_to_sms_message.errors, status=status.HTTP_400_BAD_REQUEST)

        sms_message = bandwidth_response_to_sms_message.save()
        serializer = SMSMessageSerializer(sms_message)

        return Response(serializer.data, status=status.HTTP_202_ACCEPTED)


class SMSMessageDetail(APIView):
    """
    Retrieve or update a SMSMessage instance.
    """

    def get_object(self, pk):
        try:
            return SMSMessage.objects.get(pk=pk)
        except SMSMessage.DoesNotExist:
            raise Http404

    def get(self, _, pk):
        SMSMessage = self.get_object(pk)
        serializer = SMSMessageSerializer(SMSMessage)
        return Response(serializer.data)

    def put(self, request, pk, format=None):
        SMSMessage = self.get_object(pk)
        serializer = SMSMessageSerializer(SMSMessage, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
