import json
from django.conf import settings
from django.http import Http404

from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .bandwidth.serializers import BandwidthResponseToSMSMessageSerializer, CreateMessageSerializer
from .models import SMSMessage
from .serializers import SMSMessageSerializer


class SMSMessageViewSet(viewsets.ModelViewSet):
    queryset = SMSMessage.objects.all().order_by("-created_at")
    serializer_class = SMSMessageSerializer


class SMSMessagesView(APIView):
    """
    Create a new SMSMessage.
    # TODO: list once pagination comes available
    # TODO: from_number will always come from 1 assigned group/domain's sms number, not willy-nilly

    # TODO: lock down authorization
    """

    def post(self, request, format=None):
        # Check inputs
        create_message_serializer = CreateMessageSerializer(data=request.data)
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
