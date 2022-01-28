import json
import logging
from typing import Dict, List, Tuple, Union

from django.conf import settings
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db import DatabaseError
from django.http import Http404, HttpResponseBadRequest, QueryDict
from phonenumber_field.modelfields import to_python as to_phone_number
from rest_framework import status, viewsets
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from twilio.base.exceptions import TwilioException

from core.file_upload import FileToUpload

from calls.twilio_etl import (
    get_caller_name_info_from_twilio,
    update_telecom_caller_name_info_with_twilio_data_for_valid_sections,
)
from .field_choices import (
    CallAudioFileStatusTypes,
    CallTranscriptFileStatusTypes,
    SupportedAudioMimeTypes,
    SupportedTranscriptMimeTypes,
    TelecomCallerNameInfoSourceTypes,
    TelecomCallerNameInfoTypes,
)
from .models import (
    Call,
    CallAudioPartial,
    CallLabel,
    CallPartial,
    CallTranscriptPartial,
    TelecomCallerNameInfo,
)
from .serializers import (
    CallAudioPartialSerializer,
    CallLabelSerializer,
    CallPartialSerializer,
    CallSerializer,
    CallTranscriptPartialSerializer,
    TelecomCallerNameInfoSerializer,
)

# Get an instance of a logger
log = logging.getLogger(__name__)


class CallViewset(viewsets.ModelViewSet):
    queryset = Call.objects.all().order_by("-created_at")
    serializer_class = CallSerializer


class CallTranscriptPartialViewset(viewsets.ModelViewSet):
    queryset = CallTranscriptPartial.objects.all().order_by("-created_at")
    serializer_class = CallTranscriptPartialSerializer
    filter_fields = ["call_partial", "mime_type", "status"]
    parser_classes = (JSONParser, FormParser, MultiPartParser)

    def get_queryset(self):
        return super().get_queryset().filter(call_partial=self.kwargs["call_partial_pk"])

    def update(self, request, pk=None):
        # TODO: Implement
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def data_is_valid(self, files: List) -> Union[FileToUpload, Dict]:
        if len(files) != 1:
            error_message = f"Must give 1 file per request in MultiPart Form Data."
            log.exception(error_message)
            return FileToUpload(errors=[{"files_length": error_message}])

        try:
            file = files[0]
            blob_to_upload = file[1]
            mime_type = file[0]
        except Exception:
            error_message = "In Form Data, Key must be mime_type and Value must be a file."
            return FileToUpload(errors=[{"form_data": error_message}])

        if mime_type not in SupportedTranscriptMimeTypes.values:
            error_message = f"Media type {mime_type} key form-data not in available SupportedTranscriptMimeTypes"
            log.exception(error_message)
            return FileToUpload(errors=[{"mime_type": error_message}])
        return FileToUpload(mime_type, blob_to_upload)

    def partial_update(
        self,
        request,
        pk=None,
        call_pk=None,
        call_partial_pk=None,
        format=None,
        storage_client=settings.CLOUD_STORAGE_CLIENT,
        bucket=settings.CALL_TRANSCRIPT_BUCKET,
    ):
        files = request.data.items()
        files = list(files)
        file_to_upload = self.data_is_valid(files)
        if file_to_upload.errors:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={"errors": file_to_upload.errors})
        log.info(f"Blob to upload is {file_to_upload.blob} with mimetype {file_to_upload.mime_type}.")

        # Set uploading status and mime_type on Object
        call_transcript_partial = CallTranscriptPartial.objects.get(pk=pk)
        call_transcript_partial.mime_type = file_to_upload.mime_type
        call_transcript_partial.status = CallTranscriptFileStatusTypes.UPLOADING
        call_transcript_partial.save()

        # Upload to audio bucket
        log.info(f"Saving {call_transcript_partial.pk} to bucket {bucket}")
        bucket = storage_client.get_bucket(bucket)
        blob = bucket.blob(call_transcript_partial.pk)
        blob.upload_from_string(file_to_upload.blob.read())

        log.info(f"Successfully saved {call_transcript_partial.pk} to bucket {bucket}")

        call_transcript_partial.status = CallTranscriptFileStatusTypes.UPLOADED
        call_transcript_partial.save()

        call_transcript_partial_serializer = CallTranscriptPartialSerializer(call_transcript_partial)

        return Response(status=status.HTTP_200_OK, data=call_transcript_partial_serializer.data)


class CallAudioPartialViewset(viewsets.ModelViewSet):
    queryset = CallAudioPartial.objects.all().order_by("-created_at")
    serializer_class = CallAudioPartialSerializer
    filter_fields = ["call_partial", "mime_type", "status"]
    parser_classes = (JSONParser, FormParser, MultiPartParser)

    def get_queryset(self):
        return super().get_queryset().filter(call_partial=self.kwargs["call_partial_pk"])

    def update(self, request, pk=None):
        # TODO: Implement
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def data_is_valid(self, files: List) -> Union[FileToUpload, Dict]:
        if len(files) != 1:
            error_message = f"Must give 1 file per request in MultiPart Form Data."
            log.exception(error_message)
            return FileToUpload(errors=[{"files_length": error_message}])

        try:
            file = files[0]
            blob_to_upload = file[1]
            mime_type = file[0]
        except Exception:
            error_message = "In Form Data, Key must be mime_type and Value must be a file."
            return FileToUpload(errors=[{"form_data": error_message}])

        if mime_type not in SupportedAudioMimeTypes.values:
            error_message = f"Media type {mime_type} key form-data not in available SupportedAudioMimeTypes"
            log.exception(error_message)
            return FileToUpload(errors=[{"mime_type": error_message}])
        return FileToUpload(mime_type, blob_to_upload)

    def partial_update(
        self, request, pk=None, call_pk=None, call_partial_pk=None, format=None, storage_client=settings.CLOUD_STORAGE_CLIENT, bucket=settings.CALL_AUDIO_BUCKET
    ):
        files = request.data.items()
        files = list(files)
        file_to_upload = self.data_is_valid(files)
        if file_to_upload.errors:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={"errors": file_to_upload.errors})
        log.info(f"Blob to upload is {file_to_upload.blob} with mimetype {file_to_upload.mime_type}.")

        # Set uploading status and mime_type on Object
        call_audio_partial = CallAudioPartial.objects.get(pk=pk)
        call_audio_partial.mime_type = file_to_upload.mime_type
        call_audio_partial.status = CallAudioFileStatusTypes.UPLOADING
        call_audio_partial.save()

        # Upload to audio bucket
        log.info(f"Saving {call_audio_partial.pk} to bucket {bucket}")
        bucket = storage_client.get_bucket(bucket)
        blob = bucket.blob(call_audio_partial.pk)
        blob.upload_from_string(file_to_upload.blob.read())

        log.info(f"Successfully saved {call_audio_partial.pk} to bucket {bucket}")

        call_audio_partial.status = CallAudioFileStatusTypes.UPLOADED
        call_audio_partial.save()

        call_audio_partial_serializer = CallAudioPartialSerializer(call_audio_partial)

        return Response(status=status.HTTP_200_OK, data=call_audio_partial_serializer.data)


class CallPartialViewset(viewsets.ModelViewSet):
    queryset = CallPartial.objects.all().order_by("-created_at")
    serializer_class = CallPartialSerializer

    def get_queryset(self):
        return super().get_queryset().filter(call=self.kwargs["call_pk"])


class CallLabelViewset(viewsets.ModelViewSet):
    queryset = CallLabel.objects.all().order_by("-created_at")
    serializer_class = CallLabelSerializer


class TelecomCallerNameInfoViewSet(viewsets.ModelViewSet):
    queryset = TelecomCallerNameInfo.objects.all().order_by("-modified_at")
    serializer_class = TelecomCallerNameInfoSerializer
    filter_fields = ["caller_name_type", "source"]
    search_fields = ["caller_name"]
    ordering = ["caller_name"]

    def retrieve(self, request, pk):
        phone_number_raw = pk
        log.info(f"Retrieving caller_name_info for phone_number: '{phone_number_raw}'")

        try:
            phone_number = TelecomCallerNameInfoViewSet.validate_and_normalize_phone_number(phone_number_raw=phone_number_raw)
        except Exception as e:
            return HttpResponseBadRequest(f"Invalid phone number detected, phone_number_raw: '{phone_number_raw}'")

        # use whatever we find and 404 if we don't find anything
        if not settings.TWILIO_IS_ENABLED:
            log.info(f"Twilio is off. Using existing database lookup for phone_number: '{phone_number}'")
            return super().retrieve(request, phone_number)

        # search database for record
        log.info(f"Performing lookups for phone_number: '{phone_number}'")
        telecom_caller_name_info, created = TelecomCallerNameInfo.objects.get_or_create(phone_number=phone_number)

        # existing row that has legitimate values and is not stale
        if not created and telecom_caller_name_info.caller_name_type is not None and not telecom_caller_name_info.is_caller_name_info_stale():
            log.info(f"Using existing caller_name_info from database since it exists and is not stale / expired for phone_number: '{phone_number}'.")
            return Response(TelecomCallerNameInfoSerializer(telecom_caller_name_info).data)

        # certain area codes are always business numbers if configured
        us_area_code = get_us_area_code(phone_number)
        log.info(
            f"Checking area code: '{us_area_code}' from phone_number: '{phone_number}' against known business telecom area codes: '{settings.TELECOM_AREA_CODES_TO_MARK_AS_BUSINESS_NUMBERS}'"
        )
        if us_area_code in settings.TELECOM_AREA_CODES_TO_MARK_AS_BUSINESS_NUMBERS:
            log.info(f"Area code is a known business area code for phone_number: '{phone_number}'")
            telecom_caller_name_info.source = TelecomCallerNameInfoSourceTypes.PEERLOGIC
            telecom_caller_name_info.caller_name_type = TelecomCallerNameInfoTypes.BUSINESS
            telecom_caller_name_info.save()
            return Response(TelecomCallerNameInfoSerializer(telecom_caller_name_info).data)

        # fetch from twilio and update database
        try:
            # get and validate twilio data
            log.info(f"Twilio is on and we have stale / expired or missing data. Requesting data from twilio for phone_number: '{phone_number}'")
            twilio_caller_name_info = get_caller_name_info_from_twilio(phone_number=phone_number)

            # update local object
            log.info(f"Extracting and transforming data from twilio for phone_number: '{phone_number}'.")
            update_telecom_caller_name_info_with_twilio_data_for_valid_sections(telecom_caller_name_info, twilio_caller_name_info)

            telecom_caller_name_info.save()
            log.info(f"Saved data from twilio for phone_number: '{phone_number}'")
        except TwilioException as e:
            log.exception(
                f"Unable to call Twilio to obtain or update caller name information for: '{phone_number}'. This does not mean we were unable to fulfill the request for data if we have a stale value available.",
                e,
            )
        except ValueError as e:
            log.exception(f"Problems occurred extracting values from Twilio's response for: '{phone_number}'", e)
        except DatabaseError as e:
            log.exception(
                f"Problem occurred saving updated values for phone number: '{phone_number}'. This does not mean we were unable to fulfill the request for data if we have a stale value available",
                e,
            )

        # validate that we have a legitimate value from the database
        # we may have a legitimate but stale value, that's fine
        # however, if we don't have a caller_name_type record, this is an incomplete record from our get_or_create above then roll it back / kill it
        log.info(f"Verifying we have a legitimate caller_name_info to send to client for '{phone_number}'")
        if created and (telecom_caller_name_info.caller_name_type is "" and telecom_caller_name_info.carrier_type is ""):
            log.warn(
                f"Incompleted caller_name_info record. No stale or fresh caller_name_info data is available. We've created a new caller_name_info object but couldn't fill it with Twilio values. ROLLING BACK. phone_number: '{phone_number}'"
            )
            telecom_caller_name_info.delete()
            log.warn(f"ROLLED BACK / DELETED incomplete record for phone_number: '{phone_number}'")
            raise Http404

        # win
        log.info(f"caller_name_info available to send to client for '{phone_number}'")
        return Response(TelecomCallerNameInfoSerializer(telecom_caller_name_info).data)

    @classmethod
    def validate_and_normalize_phone_number(cls, phone_number_raw: str) -> str:
        # validate and normalize phone number
        log.info(f"Validating phone number: phone_number_raw: '{phone_number_raw}'")

        # first level of normalization because we're generous with our input
        phone_number_raw = re.sub("[^0-9]", "", phone_number_raw)  # remove non-digits
        phone_number_raw = f"+{phone_number_raw}"  # add preceding plus sign

        # first validation
        phone_number = to_phone_number(phone_number_raw)  # this will explode for obviously bad phone numbers
        if not phone_number.is_valid():  # true for not so obviously bad phone numbers
            msg = f"Invalid phone number detected, phone_number_raw: '{phone_number_raw}'"
            log.error(msg)
            raise TypeError(msg)

        # be aware strange phone numbers will survive the above
        # strange phone numbers from the above include ones where a phone number has letters appended: 14401234567bb
        # strange phone numbers like this will be accepted by twilio which will truncate the bad parts
        # we MUST normalize to get something reasonable-looking for our system's storage, reduce duplicates, and reduce costs
        log.info(f"Normalizing phone_number_raw: '{phone_number_raw}'")
        phone_number = phone_number.as_e164
        log.info(f"Normalized phone_number_raw: '{phone_number_raw}' to phone_number: '{phone_number}'")

        return phone_number


def get_us_area_code(us_phone_number_in_e164: str) -> str:
    # number: +1 [234] 567 8910
    # index:  01  234  5(exclusive)
    example_phone_number = "+12345678910"
    us_phone_number_in_e164_length = len(example_phone_number)
    if len(us_phone_number_in_e164) != us_phone_number_in_e164_length:
        # this should never occur if we're using this at the appropriate point in the code
        raise TypeError(f"Invalid normalized us phone_number: '{us_phone_number_in_e164}' detected. Function used erroneously.")

    return us_phone_number_in_e164[2:5]
