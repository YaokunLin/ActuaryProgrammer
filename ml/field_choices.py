from django.db import models


class ClassificationDomain(models.TextChoices):
    NEW_PATIENT_OPPORTUNITY = "new_patient_opportunity"
    CALLER_TYPE = "caller_type" # TODO: deprecate
    CALL_PURPOSE = "call_purpose"
    CALL_OUTCOME = "call_outcome"
    CALL_OUTCOME_REASON = "call_outcome_reason"
    CALL_TRANSCRIPT_SENTIMENT = "call_transcript_sentiment"
    CALL_TRANSCRIPT_FRAGMENT_SENTIMENT = "call_transcript_fragment_sentiment"
    CALL_AUDIO_ENTHUSIASM = "call_audio_enthusiasm"
