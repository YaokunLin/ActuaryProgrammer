import json
import os
from django.conf import settings
from django.core.management.base import BaseCommand


from oauth2_provider.models import (
    get_application_model,
)
from calls.analytics.intents.models import CallMentionedInsurance, CallMentionedProcedure, CallMentionedProduct, CallMentionedSymptom
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
        call_insurance_mentioned = call.pop("call_insurance_discussed")
        call_procedure_mentioned = call.pop("call_procedure_discussed")
        call_product_mentioned = call.pop("call_product_discussed")
        call_symptom_mentioned = call.pop("call_symptom_discussed")
        call_pause = call.pop("call_pause")
        call_purpose = call.pop("call_purpose")
        non_agent_engagement_persona_info = call.pop("non_agent_engagement_persona_info")
        referral_source = call.pop("referral_source")
        del call["callee_domain"]  # TODO: remove from schema, deprecated
        del call["caller_domain"]  # TODO: remove from schema, deprecated
        del call["domain"]  # TODO: remove from schema, deprecated
        del call["metadata_file_uri"]  # TODO: remove from schema, deprecated
        del call["new_patient_opportunity_info"]  # TODO: remove from schema, never used
        del call["caller_audio_url"]
        del call["callee_audio_url"]
        del call["call_transcription"]
        del call["call_transcription_fragment"]
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

        self._load_agent_call_scores(call_agent_interactions, peerlogic_api_call)
        self._load_call_sentiment(call_sentiment, peerlogic_api_call)
        self._load_procedure_mentioned(call_procedure_mentioned, peerlogic_api_call)
        self._load_company_mentioned(call_company_mentioned, peerlogic_api_call)
        self._load_insurance_mentioned(call_insurance_mentioned, peerlogic_api_call)
        self._load_product_mentioned(call_product_mentioned, peerlogic_api_call)
        self._load_symptom_mentioned(call_symptom_mentioned, peerlogic_api_call)

    def _load_agent_call_scores(self, call_agent_interactions, call):

        for interaction in call_agent_interactions:
            metric = interaction["agent_interaction_metric_name"]
            defaults = {"raw_model_run_id": interaction["agent_interaction_metric_run_id"], "score": interaction["agent_interaction_metric_score"]}

            self.stdout.write(f"Getting or creating Agent Call Score with metric='{metric}'.")
            peerlogic_api_agent_call_score, created = AgentCallScore.objects.get_or_create(call=call, metric=metric, defaults=defaults)

            if created:
                self.stdout.write(self.style.SUCCESS(f"Created agent call score with pk='{peerlogic_api_agent_call_score.pk}'"))
            else:
                self.stdout.write(f"Not creating - Found existing agent call score with pk={peerlogic_api_agent_call_score.pk}")


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
            self.stdout.write(f"Not creating - Found existing call sentiment with pk={peerlogic_api_call_sentiment.pk}")


    def _load_procedure_mentioned(self, call_procedure_mentioned, call):

        for procedure in call_procedure_mentioned:
            keyword = procedure["call_procedure_keyword"]
            if not keyword:
                continue

            self.stdout.write(f"Getting or creating Call Mentioned Procedure with keyword='{keyword}'.")
            peerlogic_api_call_mentioned_procedure, created = CallMentionedProcedure.objects.get_or_create(
                pk=procedure["call_procedure_discussed_id"], call=call, keyword=keyword
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created call mentioned procedure with pk='{peerlogic_api_call_mentioned_procedure.pk}'"))
            else:
                self.stdout.write(f"Not creating - Found existing call mentioned procedure with pk={peerlogic_api_call_mentioned_procedure.pk}")

    def _load_company_mentioned(self, call_company_mentioned, call):

        for company in call_company_mentioned:
            keyword = company["call_company_keyword"]
            if not keyword:
                continue

            self.stdout.write(f"Getting or creating Call Mentioned Company with keyword='{keyword}'.")
            peerlogic_api_call_mentioned_company, created = CallMentionedProcedure.objects.get_or_create(
                pk=company["call_company_discussed_id"], call=call, keyword=keyword
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created call mentioned cp,[amu] with pk='{peerlogic_api_call_mentioned_company.pk}'"))
            else:
                self.stdout.write(f"Not creating - Found existing call mentioned company with pk={peerlogic_api_call_mentioned_company.pk}")

    def _load_insurance_mentioned(self, call_insurance_mentioned, call):

        for insurance in call_insurance_mentioned:
            keyword = insurance["call_insurance_keyword"]
            if not keyword:
                continue

            self.stdout.write(f"Getting or creating Call Mentioned Insurance with keyword='{keyword}'.")
            peerlogic_api_call_mentioned_insurance, created = CallMentionedInsurance.objects.get_or_create(
                pk=insurance["call_insurance_discussed_id"], call=call, keyword=keyword
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created call mentioned insurance with pk='{peerlogic_api_call_mentioned_insurance.pk}'"))
            else:
                self.stdout.write(f"Not creating - Found existing call mentioned insurance with pk={peerlogic_api_call_mentioned_insurance.pk}")

    def _load_symptom_mentioned(self, call_symptom_mentioned, call):

        for symptom in call_symptom_mentioned:
            keyword = symptom["call_symptom_keyword"]
            if not keyword:
                continue

            self.stdout.write(f"Getting or creating Call Mentioned Symptom with keyword='{keyword}'.")
            peerlogic_api_call_mentioned_symptom, created = CallMentionedSymptom.objects.get_or_create(
                pk=symptom["call_symptom_discussed_id"], call=call, keyword=keyword
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created call mentioned symptom with pk='{peerlogic_api_call_mentioned_symptom.pk}'"))
            else:
                self.stdout.write(f"Not creating - Found existing call mentioned symptom with pk={peerlogic_api_call_mentioned_symptom.pk}")

    def _load_product_mentioned(self, call_product_mentioned, call):

        for product in call_product_mentioned:
            keyword = product["call_product_keyword"]
            if not keyword:
                continue

            self.stdout.write(f"Getting or creating Call Mentioned Product with keyword='{keyword}'.")
            peerlogic_api_call_mentioned_product, created = CallMentionedProduct.objects.get_or_create(
                pk=product["call_product_discussed_id"], call=call, keyword=keyword
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created call mentioned product with pk='{peerlogic_api_call_mentioned_product.pk}'"))
            else:
                self.stdout.write(f"Not creating - Found existing call mentioned product with pk={peerlogic_api_call_mentioned_product.pk}")
