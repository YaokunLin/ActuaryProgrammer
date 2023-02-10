import logging
import re
from concurrent import futures
from typing import Dict, List, Union

from django.conf import settings
from django.db import DatabaseError, transaction
from django.http import Http404, HttpResponseBadRequest
from django_filters.rest_framework import (
    DjangoFilterBackend,  # brought in for a backend filter override
)
from google.api_core.exceptions import PermissionDenied as GooglePermissionDenied
from phonenumber_field.modelfields import to_python as to_phone_number
from rest_framework import status, views, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.filters import (
    OrderingFilter,  # brought in for a backend filter override
)
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import SAFE_METHODS
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import ValidationError
from twilio.base.exceptions import TwilioException

from calls.filters import (
    CallSearchFilter,
    CallsFilter,
    CallTranscriptsFilter,
    CallTranscriptsSearchFilter,
)
from calls.publishers import (
    publish_call_audio_partial_saved,
    publish_call_audio_saved,
    publish_call_transcript_saved,
)
from calls.twilio_etl import (
    get_caller_name_info_from_twilio,
    update_telecom_caller_name_info_with_twilio_data_for_valid_sections,
)
from calls.validation import get_validated_query_param_bool
from core.file_upload import FileToUpload
from core.models import Agent, InsuranceProviderPhoneNumber

from .field_choices import (
    CallAudioFileStatusTypes,
    CallConnectionTypes,
    CallDirectionTypes,
    CallTranscriptFileStatusTypes,
    ReferralSourceTypes,
    SentimentTypes,
    SpeechToTextModelTypes,
    SupportedAudioMimeTypes,
    SupportedTranscriptMimeTypes,
    TelecomCallerNameInfoSourceTypes,
    TelecomCallerNameInfoTypes,
    TelecomPersonaTypes,
    TranscriptTypes,
)
from .models import (
    Call,
    CallAudio,
    CallAudioPartial,
    CallLabel,
    CallNote,
    CallPartial,
    CallTranscript,
    CallTranscriptPartial,
    TelecomCallerNameInfo,
)
from .serializers import (
    CallAudioPartialReadOnlySerializer,
    CallAudioPartialSerializer,
    CallAudioSerializer,
    CallDetailsSerializer,
    CallLabelSerializer,
    CallNoteReadSerializer,
    CallNoteWriteSerializer,
    CallPartialSerializer,
    CallSerializer,
    CallTranscriptPartialReadOnlySerializer,
    CallTranscriptPartialSerializer,
    CallTranscriptSerializer,
    TelecomCallerNameInfoSerializer,
)

# Get an instance of a logger
log = logging.getLogger(__name__)


class CallFieldChoicesView(views.APIView):
    def get(self, request, format=None):
        result = {}
        result["call_connection_types"] = dict((y, x) for x, y in CallConnectionTypes.choices)
        result["call_direction_types"] = dict((y, x) for x, y in CallDirectionTypes.choices)
        result["telecom_persona_types"] = dict((y, x) for x, y in TelecomPersonaTypes.choices)
        result["referral_source_types"] = dict((y, x) for x, y in ReferralSourceTypes.choices)
        result["telecom_caller_name_info_types"] = dict((y, x) for x, y in TelecomCallerNameInfoTypes.choices)
        # result["audio_codec_types"] = dict((y, x) for x, y in AudioCodecType.choices)
        result["call_audio_file_status_types"] = dict((y, x) for x, y in CallAudioFileStatusTypes.choices)
        result["call_transcript_file_status_types"] = dict((y, x) for x, y in CallTranscriptFileStatusTypes.choices)
        result["supported_audio_mime_types"] = dict((y, x) for x, y in SupportedAudioMimeTypes.choices)
        result["supported_transcript_mime_types"] = dict((y, x) for x, y in SupportedTranscriptMimeTypes.choices)
        result["transcript_types"] = dict((y, x) for x, y in TranscriptTypes.choices)
        result["speech_to_text_model_types"] = dict((y, x) for x, y in SpeechToTextModelTypes.choices)
        result["sentiment_types"] = dict((y, x) for x, y in SentimentTypes.choices)
        # TODO: PTECH-1240
        result["marketing_campaign_names"] = {"Mailer": "mailer", "Google My Business": "gmb", "Main": "main"}  # TODO: Unfuck this
        return Response(result)


class CallViewset(viewsets.ModelViewSet):
    queryset = Call.objects.all().order_by("-call_start_time")
    serializer_class = CallSerializer
    filterset_class = CallsFilter

    filter_backends = (
        DjangoFilterBackend,
        CallSearchFilter,
        OrderingFilter,
    )  # note: these must be kept up to date with settings.py values!
    ordering_fields = (
        "id",
        "call_direction",
        "call_start_time",
        "sip_caller_number",
        "sip_caller_extension",
        "sip_callee_number",
        "sip_callee_extension",
        "call_connection",
        "checked_voicemail",
        "went_to_voicemail",
        "engaged_in_calls__non_agent_engagement_persona_type",
        "call_purposes__call_purpose_type",
        "call_purposes__outcome_results__call_outcome_type",
        "call_sentiments__overall_sentiment_score",
    )

    def get_queryset(self):
        calls_qs = Call.objects.none()

        if self.request.user.is_staff or self.request.user.is_superuser:
            calls_qs = Call.objects.all()
        elif self.request.method in SAFE_METHODS:
            # Can see any practice's calls if you are an assigned agent to a practice
            practice_ids = Agent.objects.filter(user=self.request.user).values_list("practice_id", flat=True)
            calls_qs = Call.objects.filter(practice__id__in=practice_ids)

        query_set = CallSerializer.apply_queryset_prefetches(calls_qs)
        # TODO: Figure out total_value annotation below?

        return query_set.order_by("-call_start_time")

    def retrieve(self, request: Request, *args, **kwargs):
        instance = self.get_object()
        serializer = CallDetailsSerializer(instance)
        return Response(serializer.data)


class GetCallAudioPartial(ListAPIView):
    queryset = CallAudioPartial.objects.all().select_related("call_partial").order_by("call_partial__time_interaction_started", "-modified_at")
    serializer_class = CallAudioPartialReadOnlySerializer


class GetCallAudioPartials(ListAPIView):
    queryset = CallAudioPartial.objects.all().select_related("call_partial").order_by("call_partial__time_interaction_started", "-modified_at")
    serializer_class = CallAudioPartialReadOnlySerializer
    filter_fields = ["call_partial", "call_partial__call", "mime_type", "status"]


class GetCallTranscriptPartial(RetrieveAPIView):
    queryset = CallTranscriptPartial.objects.all().select_related("call_partial").order_by("call_partial__time_interaction_started", "modified_at")
    serializer_class = CallTranscriptPartialReadOnlySerializer


class GetCallTranscriptPartials(ListAPIView):
    queryset = CallTranscriptPartial.objects.all().select_related("call_partial").order_by("call_partial__time_interaction_started", "-modified_at")
    serializer_class = CallTranscriptPartialReadOnlySerializer
    filter_fields = ["call_partial", "call_partial__call", "mime_type", "status", "transcript_type", "speech_to_text_model_type"]


class CallAudioViewset(viewsets.ModelViewSet):
    queryset = CallAudio.objects.all().order_by("-modified_at")
    serializer_class = CallAudioSerializer
    filter_fields = ["call", "mime_type", "status"]
    parser_classes = (JSONParser, FormParser, MultiPartParser)

    def get_queryset(self):
        return super().get_queryset().filter(call=self.kwargs.get("call_pk"))

    def update(self, request, pk=None):
        # TODO: Implement
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @action(detail=True, methods=["post"])
    def publish_call_audio_saved(self, request, call_pk=None, pk=None):

        log.info(f"Publishing call audio saved event for: call_audio_id: '{pk}'")
        publish_future = publish_call_audio_saved(call_id=call_pk, call_audio_id=pk)
        log.info(f"Published call audio saved event for: call_audio_id: '{pk}'")

        # TODO: figure out how to detect errors from error handler and respond with 403
        # ideally without slow-downs
        # most common error is the following when first getting started
        # GooglePermissionDenied - Must add role 'roles/pubsub.publisher'
        return Response(status=status.HTTP_200_OK, data={"status": "published"})

    def data_is_valid(self, files: List) -> Union[FileToUpload, Dict]:
        if len(files) != 1:
            error_message = f"Must give 1 file per request in MultiPart Form Data."
            log.exception(error_message)
            raise ValidationError({"errors": [{"files_length": error_message}]})

        try:
            file = files[0]
            blob_to_upload = file[1]
            mime_type = file[0]
        except Exception:
            error_message = "In Form Data, Key must be mime_type and Value must be a file."
            raise ValidationError({"errors": [{"files_length": error_message}]})

        if mime_type not in SupportedAudioMimeTypes.values:
            error_message = f"Media type {mime_type} key form-data not in available SupportedTranscriptMimeTypes"
            log.exception(error_message)
            raise ValidationError({"errors": [{"files_length": error_message}]})
        return FileToUpload(mime_type, blob_to_upload)

    def partial_update(
        self,
        request,
        pk=None,
        call_pk=None,
        format=None,
        storage_client=settings.CLOUD_STORAGE_CLIENT,
        bucket=settings.BUCKET_NAME_CALL_AUDIO,
    ):
        files = request.data.items()
        files = list(files)
        file_to_upload = self.data_is_valid(files)
        log.info(f"Blob to upload is {file_to_upload.blob} with mimetype {file_to_upload.mime_type}.")

        # Set uploading status and mime_type on Object
        log.info(f"Saving object with uploading status and mime type to the database.")
        call_audio = CallAudio.objects.get(pk=pk)
        with transaction.atomic():
            call_audio.mime_type = file_to_upload.mime_type
            call_audio.status = CallAudioFileStatusTypes.UPLOADING
            call_audio.save()
            log.info(f"Saved object with uploading status and mime type to the database.")

        # Upload to audio bucket
        log.info(f"Saving {call_audio.pk} file to bucket {bucket}")
        bucket = storage_client.get_bucket(bucket)
        blob = bucket.blob(call_audio.pk)
        blob.upload_from_string(file_to_upload.blob.read(), content_type=call_audio.mime_type)
        log.info(f"Successfully saved {call_audio.pk} to bucket {bucket}")

        log.info(f"Saving object with uploaded status to the database.")
        with transaction.atomic():
            call_audio.status = CallAudioFileStatusTypes.UPLOADED
            call_audio.save()
            log.info(f"Saved object with uploaded status to the database.")

        call_audio_serializer = CallAudioSerializer(call_audio)

        #
        # PROCESSING
        #
        try:
            log.info(f"Publishing call audio saved events for: call_audio_id: '{call_audio.pk}'")
            publish_call_audio_saved(call_id=call_pk, call_audio_id=call_audio.pk)
            log.info(f"Published call audio saved events for: call_audio_id: '{call_audio.pk}'")
        except GooglePermissionDenied:
            message = "Must add role 'roles/pubsub.publisher'. Exiting."
            log.exception(message)
            return Response(status=status.HTTP_403_FORBIDDEN, data={"error": message})

        return Response(status=status.HTTP_200_OK, data=call_audio_serializer.data)


class CallTranscriptViewset(viewsets.ModelViewSet):
    queryset = CallTranscript.objects.all().order_by("-modified_at")
    serializer_class = CallTranscriptSerializer
    filter_fields = ["call", "mime_type", "status", "transcript_type", "speech_to_text_model_type"]
    filter_backends = (
        DjangoFilterBackend,
        CallTranscriptsSearchFilter,
        OrderingFilter,
    )  # note: these must be kept up to date with settings.py values!
    filterset_class = CallTranscriptsFilter
    parser_classes = (JSONParser, FormParser, MultiPartParser)

    def get_queryset(self):
        queryset = super().get_queryset().filter(call=self.kwargs.get("call_pk"))
        return queryset

    def update(self, request, pk=None, call_pk=None):
        data = dict(request.data)
        data["call"] = call_pk
        try:
            call_transcript = CallTranscript.objects.get(pk=pk)
        except CallTranscript.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND, data={"id": f"No call transcript with id={pk}."})

        try:
            Call.objects.get(pk=call_pk)
        except Call.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND, data={"id": f"No call transcript with call__id={pk}."})

        call_transcript_serializer = CallTranscriptSerializer(call_transcript, data=data)
        call_transcript_serializer_is_valid = call_transcript_serializer.is_valid()
        if not call_transcript_serializer_is_valid:
            return Response(call_transcript_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Update the record in the database
        call_transcript_serializer.save()
        return Response(status=status.HTTP_200_OK, data=call_transcript_serializer.data)

    def data_is_valid(self, files: List) -> Union[FileToUpload, Dict]:
        if len(files) != 1:
            error_message = f"Must give 1 file per request in MultiPart Form Data."
            log.exception(error_message)
            raise ValidationError({"errors": [{"files_length": error_message}]})

        try:
            file = files[0]
            blob_to_upload = file[1]
            mime_type = file[0]
        except Exception:
            error_message = "In Form Data, Key must be mime_type and Value must be a file."
            raise ValidationError({"errors": [{"files_length": error_message}]})

        if mime_type not in SupportedTranscriptMimeTypes.values:
            error_message = f"Media type {mime_type} key form-data not in available SupportedTranscriptMimeTypes"
            log.exception(error_message)
            raise ValidationError({"errors": [{"files_length": error_message}]})
        return FileToUpload(mime_type, blob_to_upload)

    def partial_update(
        self,
        request,
        pk=None,
        call_pk=None,
        format=None,
        storage_client=settings.CLOUD_STORAGE_CLIENT,
        bucket=settings.BUCKET_NAME_CALL_TRANSCRIPT,
    ):
        files = request.data.items()
        files = list(files)
        file_to_upload = self.data_is_valid(files)
        log.info(f"Blob to upload is {file_to_upload.blob} with mimetype {file_to_upload.mime_type}.")

        # Set uploading status and mime_type on Object
        log.info(f"Saving object with uploading status and mime type to the database.")
        call_transcript = CallTranscript.objects.get(pk=pk)
        with transaction.atomic():
            call_transcript.mime_type = file_to_upload.mime_type
            call_transcript.status = CallTranscriptFileStatusTypes.UPLOADING
            call_transcript.save()
            log.info(f"Saved object with uploading status and mime type to the database.")

        # Upload to audio bucket
        log.info(f"Saving {call_transcript.pk} file to bucket {bucket}")
        bucket = storage_client.get_bucket(bucket)
        blob = bucket.blob(call_transcript.file_basename)
        blob.upload_from_string(file_to_upload.blob.read())
        log.info(f"Successfully saved {call_transcript.pk} to bucket {bucket}")

        log.info(f"Saving object with uploaded status to the database.")
        with transaction.atomic():
            call_transcript.status = CallTranscriptFileStatusTypes.UPLOADED
            call_transcript.save()
            log.info(f"Saved object with uploaded status to the database.")

        call_transcript_serializer = CallTranscriptSerializer(call_transcript)

        #
        # PROCESSING
        #
        if not call_transcript.publish_event_on_patch:
            log.info(
                f"Not publishing to topic for call_transcript_id: '{call_transcript.pk}'; call_transcript.publish_event_on_patch='{call_transcript.publish_event_on_patch}' set to False"
            )
            return Response(status=status.HTTP_200_OK, data=call_transcript_serializer.data)

        try:
            log.info(f"Publishing call transcript ready events for: call_transcript_id: '{call_transcript.pk}'")
            publish_call_transcript_saved(call_id=call_pk, call_transcript_id=call_transcript.pk)
            log.info(f"Published call transcript ready events for: call_transcript_id: '{call_transcript.pk}'")
        except GooglePermissionDenied:
            message = "Must add role 'roles/pubsub.publisher'. Exiting."
            log.exception(message)
            return Response(status=status.HTTP_403_FORBIDDEN, data={"error": message})

        return Response(status=status.HTTP_200_OK, data=call_transcript_serializer.data)


class CallTranscriptPartialViewset(viewsets.ModelViewSet):
    queryset = CallTranscriptPartial.objects.all().order_by("-created_at")
    serializer_class = CallTranscriptPartialSerializer
    filter_fields = ["call_partial", "mime_type", "status"]
    parser_classes = (JSONParser, FormParser, MultiPartParser)

    def get_queryset(self):
        return super().get_queryset().filter(call_partial=self.kwargs.get("call_partial_pk"))

    def update(self, request, pk=None):
        # TODO: Implement
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def data_is_valid(self, files: List) -> Union[FileToUpload, Dict]:
        if len(files) != 1:
            error_message = f"Must give 1 file per request in MultiPart Form Data."
            log.exception(error_message)
            raise ValidationError({"errors": [{"files_length": error_message}]})

        try:
            file = files[0]
            blob_to_upload = file[1]
            mime_type = file[0]
        except Exception:
            error_message = "In Form Data, Key must be mime_type and Value must be a file."
            raise ValidationError({"errors": [{"files_length": error_message}]})

        if mime_type not in SupportedTranscriptMimeTypes.values:
            error_message = f"Media type {mime_type} key form-data not in available SupportedTranscriptMimeTypes"
            log.exception(error_message)
            raise ValidationError({"errors": [{"files_length": error_message}]})
        return FileToUpload(mime_type, blob_to_upload)

    def partial_update(
        self,
        request,
        pk=None,
        call_pk=None,
        call_partial_pk=None,
        format=None,
        storage_client=settings.CLOUD_STORAGE_CLIENT,
        bucket=settings.BUCKET_NAME_CALL_TRANSCRIPT_PARTIAL,
    ):
        files = request.data.items()
        files = list(files)
        file_to_upload = self.data_is_valid(files)
        log.info(f"Blob to upload is {file_to_upload.blob} with mimetype {file_to_upload.mime_type}.")

        # Set uploading status and mime_type on Object
        log.info(f"Saving object with uploading status and mime type to the database.")
        call_transcript_partial = CallTranscriptPartial.objects.get(pk=pk)
        with transaction.atomic():
            call_transcript_partial.mime_type = file_to_upload.mime_type
            call_transcript_partial.status = CallTranscriptFileStatusTypes.UPLOADING
            call_transcript_partial.save()
            log.info(f"Saved object with uploading status and mime type to the database.")

        # Upload to audio bucket
        log.info(f"Saving {call_transcript_partial.pk} to bucket {bucket}")
        bucket = storage_client.get_bucket(bucket)
        log.info(f"call_transcript_partial.file_basename = {call_transcript_partial.file_basename}")
        blob = bucket.blob(call_transcript_partial.file_basename)
        blob.upload_from_string(file_to_upload.blob.read())
        log.info(f"signed_url {call_transcript_partial.signed_url}")
        log.info(f"Successfully saved {call_transcript_partial.pk} to bucket {bucket}")

        log.info(f"Saving object with uploaded status to the database.")
        with transaction.atomic():
            call_transcript_partial.status = CallTranscriptFileStatusTypes.UPLOADED
            call_transcript_partial.save()
            log.info(f"Saved object with uploaded status to the database.")

        call_transcript_partial_serializer = CallTranscriptPartialSerializer(call_transcript_partial)

        return Response(status=status.HTTP_200_OK, data=call_transcript_partial_serializer.data)


class CallAudioPartialViewset(viewsets.ModelViewSet):
    queryset = CallAudioPartial.objects.all().order_by("-created_at")
    serializer_class = CallAudioPartialSerializer
    filter_fields = ["call_partial", "mime_type", "status"]
    parser_classes = (JSONParser, FormParser, MultiPartParser)

    def get_queryset(self):
        return super().get_queryset().filter(call_partial=self.kwargs.get("call_partial_pk"))

    @action(detail=True, methods=["post"])
    def publish_call_audio_partial_saved(self, request, call_pk=None, call_partial_pk=None, pk=None):
        try:
            log.info(f"Republishing call audio partial ready events for: call_audio_partial_id: '{pk}'")
            publish_call_audio_partial_saved(call_id=call_pk, partial_id=call_partial_pk, audio_partial_id=pk)
            log.info(f"Republished call audio partial ready events for: call_audio_partial_id: '{pk}'")
            return Response(status=status.HTTP_200_OK, data={"status": "published"})
        except GooglePermissionDenied:
            message = "Must add role 'roles/pubsub.publisher'. Exiting."
            log.exception(message)
            return Response(status=status.HTTP_403_FORBIDDEN, data={"error": message})

    def data_is_valid(self, files: List) -> Union[FileToUpload, Dict]:
        if len(files) != 1:
            error_message = f"Must give 1 file per request in MultiPart Form Data."
            log.exception(error_message)
            raise ValidationError({"errors": [{"files_length": error_message}]})

        try:
            file = files[0]
            blob_to_upload = file[1]
            mime_type = file[0]
        except Exception:
            error_message = "In Form Data, Key must be mime_type and Value must be a file."
            raise ValidationError({"errors": [{"files_length": error_message}]})

        if mime_type not in SupportedAudioMimeTypes.values:
            error_message = f"Media type {mime_type} key form-data not in available SupportedAudioMimeTypes"
            log.exception(error_message)
            raise ValidationError({"errors": [{"files_length": error_message}]})
        return FileToUpload(mime_type, blob_to_upload)

    @action(detail=True, methods=["patch"])
    def upload_file(
        self,
        request,
        pk=None,
        call_pk=None,
        call_partial_pk=None,
        format=None,
        storage_client=settings.CLOUD_STORAGE_CLIENT,
        bucket=settings.BUCKET_NAME_CALL_AUDIO_PARTIAL,
    ) -> Response:
        files = request.data.items()
        files = list(files)
        file_to_upload = self.data_is_valid(files)
        log.info(f"Blob to upload is {file_to_upload.blob} with mimetype {file_to_upload.mime_type}.")

        # Set uploading status and mime_type on Object
        log.info(f"Saving object with uploading status and mime type to the database. call_audio_partial='{pk}'")
        call_audio_partial = CallAudioPartial.objects.get(pk=pk)
        with transaction.atomic():
            call_audio_partial.mime_type = file_to_upload.mime_type
            call_audio_partial.status = CallAudioFileStatusTypes.UPLOADING
            call_audio_partial.save()
            log.info(f"Saved object with uploading status and mime type to the database. call_audio_partial='{call_audio_partial.id}'")

        # Upload to audio bucket
        log.info(f"Saving {call_audio_partial.pk} to bucket {bucket}")
        bucket = storage_client.get_bucket(bucket)
        blob = bucket.blob(call_audio_partial.pk)
        blob.upload_from_string(file_to_upload.blob.read(), content_type=call_audio_partial.mime_type)
        log.info(f"Successfully saved {call_audio_partial.pk} to bucket {bucket}")

        log.info(f"Saving object with uploaded status UPLOADED. call_audio_partial='{call_audio_partial.id}'")
        with transaction.atomic():
            call_audio_partial.status = CallAudioFileStatusTypes.UPLOADED
            call_audio_partial.save()
            log.info(f"Saved object with uploading status UPLOADED. call_audio_partial='{call_audio_partial.id}'")

        call_audio_partial_serializer = CallAudioPartialSerializer(call_audio_partial)

        #
        # PROCESSING
        #

        try:
            log.info(f"Publishing call audio partial ready events for: call_audio_partial_id: '{call_audio_partial.id}'")
            publish_call_audio_partial_saved(call_id=call_pk, partial_id=call_partial_pk, audio_partial_id=call_audio_partial.id)
            log.info(f"Published call audio partial ready events for: call_audio_partial_id: '{call_audio_partial.id}'")
        except GooglePermissionDenied:
            message = "Must add role 'roles/pubsub.publisher'. Exiting."
            log.exception(message)
            return Response(status=status.HTTP_403_FORBIDDEN, data={"error": message})

        return Response(status=status.HTTP_200_OK, data=call_audio_partial_serializer.data)


class CallPartialViewset(viewsets.ModelViewSet):
    queryset = CallPartial.objects.all().order_by("-created_at")
    serializer_class = CallPartialSerializer
    filter_fields = ["call", "time_interaction_started", "time_interaction_ended"]

    def get_queryset(self):
        return super().get_queryset().filter(call=self.kwargs.get("call_pk"))


class CallLabelViewset(viewsets.ModelViewSet):
    queryset = CallLabel.objects.all().order_by("-created_at")
    serializer_class = CallLabelSerializer
    filter_fields = ["call__id"]


class CallNoteViewSet(viewsets.ModelViewSet):
    queryset = CallNote.objects.all().order_by("created_at")
    serializer_class_read = CallNoteReadSerializer
    serializer_class_write = CallNoteWriteSerializer
    filter_fields = ["call__id"]

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return self.serializer_class_write

        return self.serializer_class_read

    def get_queryset(self):
        return super().get_queryset().filter(call=self.kwargs.get("call_pk"))


class CallsReprocessingView(views.APIView):
    MAX_CALLS_PER_REQUEST = 500

    def post(self, request: Request) -> Response:
        if not self.request.user.is_staff and not self.request.user.is_superuser:
            raise PermissionDenied()

        calls_qs = CallSerializer.apply_queryset_prefetches(Call.objects.all())

        should_commit = get_validated_query_param_bool(request, "commit", False)

        filter = CallsFilter(request=request, data=request.query_params)
        is_valid = filter.is_valid()
        if not is_valid:
            return Response(data={"errors": filter.errors}, status=400)

        calls_qs = filter.filter_queryset(queryset=calls_qs)
        transcripts_to_reprocess = (
            CallTranscript.objects.filter(
                call_id__in=calls_qs.values_list("id", flat=True).distinct(),
                transcript_type=TranscriptTypes.FULL_TEXT,
            )
            .order_by("call_id", "-created_at")
            .distinct("call_id")
            .values_list("call_id", "id")
        )
        num_calls_to_reprocess = len(transcripts_to_reprocess)

        if should_commit:
            if num_calls_to_reprocess > self.MAX_CALLS_PER_REQUEST:
                raise ValidationError(
                    {"errors": [{"commit": f"This would reprocess {num_calls_to_reprocess} at once. The maximum allowed is {self.MAX_CALLS_PER_REQUEST}"}]}
                )
            publish_futures = []
            for call_id, transcript_id in transcripts_to_reprocess:
                log.info("Publishing call transcript ready events for call_id: %s, transcript_id: %s", call_id, transcript_id)
                publish_futures.append(publish_call_transcript_saved(call_id=call_id, call_transcript_id=transcript_id))
            if publish_futures:
                futures.wait(publish_futures, return_when=futures.ALL_COMPLETED)
                log.info("Successfully published all call transcript ready events")

        data = {"calls_to_reprocess": num_calls_to_reprocess, "committed": should_commit}
        return Response(data)


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

        # Check for insurance providers
        is_known_insurance_provider = InsuranceProviderPhoneNumber.objects.filter(phone_number=phone_number).exists()

        # search database for record
        log.info(f"Performing lookups for phone_number: '{phone_number}'")
        telecom_caller_name_info, created = TelecomCallerNameInfo.objects.get_or_create(phone_number=phone_number)

        if telecom_caller_name_info.is_known_insurance_provider != is_known_insurance_provider:
            telecom_caller_name_info.is_known_insurance_provider = is_known_insurance_provider
            telecom_caller_name_info.save()

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

        if not settings.TWILIO_IS_ENABLED:
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
                f"Unable to call Twilio to obtain or update caller name information for: '{phone_number}'. This does not mean we were unable to fulfill the request for data if we have a stale value available."
            )
        except ValueError as e:
            log.exception(f"Problems occurred extracting values from Twilio's response for: '{phone_number}'")
        except DatabaseError as e:
            log.exception(
                f"Problem occurred saving updated values for phone number: '{phone_number}'. This does not mean we were unable to fulfill the request for data if we have a stale value available"
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
