import json
import os
from django.conf import settings
from django.core.management.base import BaseCommand


from oauth2_provider.models import (
    get_application_model,
)
from calls.analytics.interactions.models import AgentCallScore
from calls.analytics.transcripts.models import CallSentiment
from calls.field_choices import SentimentTypes
from calls.models import Call
from core.models import Practice

Application = get_application_model()


class Command(BaseCommand):
    help = "Loads Peerlogic API with json values extracted from BigQuery call table."

    def add_arguments(self, parser):
        parser.add_argument("relative_file_path", type=str)
        parser.add_argument("practice_id", type=str)

    def handle(self, *args, **options):
        self.stdout.write(f"Going to database to obtain practice object for practice_id='{options['practice_id']}")
        try:
            practice = Practice.objects.get(pk=options["practice_id"])
        except Practice.DoesNotExist:
            self.stderr.write(f"Practice practice_id='{options['practice_id']}' does not exist! Exiting.")
            exit(2)

        self.stdout.write(f"Loading file options['relative_file_path']={options['relative_file_path']}")
        relative_file_path = options["relative_file_path"]
        absolute_file_path = os.path.join(settings.BASE_DIR, relative_file_path)
        if not os.path.exists(absolute_file_path):
            self.stderr.write("File does not exist! Exiting.")
            exit(2)

        calls = None
        with open(absolute_file_path, "r") as f:
            calls = json.load(f)

        self.stdout.write(f"Loaded file {absolute_file_path}")

        call = calls[0]
        # TODO: Replace with for loop
        self.stdout.write(f"Getting or creating call with call['call_id']='{call['call_id']}'")
        call_id = call.pop("call_id")
        defaults = {}
        defaults.update(
            {
                "id": call_id,
                "call_start_time": call.pop("call_start"),
                "call_end_time": call.pop("call_end"),
                "practice": practice,
                "checked_voicemail": bool(call.pop("checked_voicemail")),
                "went_to_voicemail": bool(call.pop("went_to_voicemail")),
            }
        )

        call_sentiment = call.pop("call_sentiment")
        call_agent_interactions = call.pop("call_agent_interaction")
        call_company_mentioned = call.pop("call_company_discussed")
        call_pause = call.pop("call_pause")
        call_procedure_mentioned = call.pop("call_procedure_discussed")
        call_product_mentioned = call.pop("call_product_discussed")
        call_purpose = call.pop("call_purpose")
        call_symptom_mentioned = call.pop("call_symptom_discussed")
        call_transcription = call.pop("call_transcription")
        call_transcription_fragment = call.pop("call_transcription_fragment")
        callee_audio_url = call.pop("callee_audio_url")
        caller_audio_url = call.pop("caller_audio_url")
        non_agent_engagement_persona_info = call.pop("non_agent_engagement_persona_info")
        referral_source = call.pop("referral_source")
        del call["practice_id"]
        del call["caller_type_info"]
        del call["insert_timestamp"]
        del call["site_id"]

        print(call)

        defaults.update(call)
        peerlogic_api_call, created = Call.objects.get_or_create(pk=call_id, defaults=defaults)
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created call with pk='{peerlogic_api_call.pk}'"))

        self.stdout.write(f"Working with Peerlogic Call {peerlogic_api_call.pk}")

        self._load_call_sentiment(call_sentiment, peerlogic_api_call)
        self._load_agent_call_scores(call_agent_interactions, peerlogic_api_call)

    def _load_call_sentiment(self, call_sentiment, call):
        BQ_TO_PEERLOGIC_API_SENTIMENT_TYPE_MAP = {
            "positive": SentimentTypes.POSITIVE,
            "negative": SentimentTypes.NEGATIVE,
            "neutral": SentimentTypes.NEUTRAL,
            "n/a": SentimentTypes.NOT_APPLICABLE,
        }

        defaults = {
            "overall_sentiment_score": BQ_TO_PEERLOGIC_API_SENTIMENT_TYPE_MAP[call_sentiment["overall_sentiment"]],
            "caller_sentiment_score": BQ_TO_PEERLOGIC_API_SENTIMENT_TYPE_MAP[call_sentiment["caller_sentiment"]],
            "callee_sentiment_score": BQ_TO_PEERLOGIC_API_SENTIMENT_TYPE_MAP[call_sentiment["callee_sentiment"]],
            "raw_call_sentiment_model_run_id": call_sentiment["sentiment_run_id"],
        }

        self.stdout.write(f"Getting or creating Call Sentiment.")
        peerlogic_api_call_sentiment, created = CallSentiment.objects.get_or_create(call=call, defaults=defaults)

        if created:
            self.stdout.write(self.style.SUCCESS(f"Created call sentiment with pk='{peerlogic_api_call_sentiment.pk}'"))
        else:
            self.stdout.write(f"Found Call Sentiment with pk={peerlogic_api_call_sentiment.pk}")

    def _load_agent_call_scores(self, call_agent_interactions, call):

        for interaction in call_agent_interactions:
            metric = interaction["agent_interaction_metric_name"]
            defaults = {"raw_model_run_id": interaction["agent_interaction_metric_run_id"], "score": interaction["agent_interaction_metric_score"]}

            self.stdout.write(f"Getting or creating Agent Call Score with metric='{metric}'.")
            peerlogic_api_agent_call_score, created = AgentCallScore.objects.get_or_create(call=call, metric=metric, defaults=defaults)

            if created:
                self.stdout.write(self.style.SUCCESS(f"Created agent call score with pk='{peerlogic_api_agent_call_score.pk}'"))
            else:
                self.stdout.write(f"Found Agent Call Score with pk={peerlogic_api_agent_call_score.pk}")
