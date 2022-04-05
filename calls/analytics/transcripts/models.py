import logging
from core.abstract_models import AuditTrailModel
from django.conf import settings
from django.db import models
from django_extensions.db.fields import ShortUUIDField

from calls.field_choices import SentimentTypes, TelecomPersonaTypes

# Get an instance of a logger
log = logging.getLogger(__name__)

# TODO: Move full CallTranscript model here


class CallSentiment(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    call = models.ForeignKey("Call", on_delete=models.CASCADE, verbose_name="Sentiment score of the call", related_name="call_sentiments")
    overall_sentiment_score = models.CharField(choices=SentimentTypes.choices, max_length=50)
    caller_sentiment_score = models.CharField(choices=SentimentTypes.choices, max_length=50)
    callee_sentiment_score = models.CharField(choices=SentimentTypes.choices, max_length=50)
    raw_call_sentiment_model_run_id = models.CharField(max_length=22)
    # TODO: Foreign key of call_sentiment_model_run to results history when available


class CallTranscriptFragment(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    call = models.ForeignKey(
        "Call", on_delete=models.CASCADE, verbose_name="a piece of a conversation from a call transcript", related_name="transcript_fragments"
    )
    time_start = models.DateTimeField()
    time_end = models.DateTimeField()
    text = models.TextField()
    telecom_persona_type = models.CharField(choices=TelecomPersonaTypes.choices, max_length=50)
    # TODO: generate by sentiment line by line model, it's currently a regression to use sentiment model
    raw_call_transcript_fragment_model_run_id = models.CharField(max_length=22)
    # TODO: Foreign key of call_transcript_fragment_model_run to results history when available


class CallTranscriptFragmentSentiment(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    call_transcript_fragment = models.ForeignKey(
        CallTranscriptFragment,
        on_delete=models.CASCADE,
        verbose_name="sentiment on a piece of a conversation from a call transcript",
        related_name="transcript_fragment_sentiments",
    )
    sentiment_score = models.CharField(choices=SentimentTypes.choices, max_length=50)
    raw_call_transcript_fragment_sentiment_model_run_id = models.CharField(max_length=22)
    # TODO: Foreign key of call_transcript_fragmentsentiment__model_run to results history when available


class CallLongestPause(AuditTrailModel):
    id = ShortUUIDField(primary_key=True, editable=False)
    call = models.ForeignKey(
        "Call", on_delete=models.CASCADE, verbose_name="a pause in conversation detected in the audio or transcript", related_name="call_pauses"
    )
    duration = models.DurationField()  # longest_pause in BQ
    # in BQ, these next 2 fields are start_time and end_time, in decimal form. This is more ideal.
    time_start = models.DateTimeField()
    time_end = models.DateTimeField()
    raw_call_pause_model_run_id = models.CharField(max_length=22)
    # TODO: Foreign key of call_pause_model_run to results history when available
