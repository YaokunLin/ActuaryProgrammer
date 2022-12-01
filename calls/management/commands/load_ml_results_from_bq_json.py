import json

from typing import Dict
from django.conf import settings
from django.core.management.base import BaseCommand


from google.cloud import storage
from oauth2_provider.models import (
    get_application_model,
)
from calls.analytics.intents.field_choices import CallOutcomeReasonTypes, CallOutcomeTypes
from calls.analytics.intents.models import (
    CallMentionedInsurance,
    CallMentionedProcedure,
    CallMentionedProduct,
    CallMentionedSymptom,
    CallOutcome,
    CallOutcomeReason,
    CallPurpose,
)
from calls.analytics.interactions.models import AgentCallScore
from calls.analytics.participants.field_choices import NonAgentEngagementPersonaTypes
from calls.analytics.participants.models import AgentEngagedWith
from calls.analytics.transcripts.models import CallSentiment
from calls.field_choices import ReferralSourceTypes, SentimentTypes
from calls.models import Call
from core.models import Practice

Application = get_application_model()


class Command(BaseCommand):
    help = "Loads Peerlogic API with jsonl values extracted from BigQuery call table."

    def add_arguments(self, parser):
        parser.add_argument("month", type=str, help="month string is <YYYY-MM>")
        parser.add_argument("--practice-id", type=str)
        parser.add_argument("--starting-blobname", type=str, help="format is <YYYY-MM/000000000002.json>")

    def handle(self, *args, **options):

        month = options["month"]
        starting_blobname = options["starting_blobname"]

        bucket_name = settings.BUCKET_NAME_BQ_CALL_ANALYTICS_EXTRACTS
        self.stdout.write(
            f"Loading blobs as configured by env-var 'BUCKET_NAME_BQ_CALL_ANALYTICS_EXTRACTS' bucket_name='{bucket_name}' with options['month']={month}, starting at options['starting_blobname']='{starting_blobname}'"
        )
        bucket = storage.Bucket(settings.CLOUD_STORAGE_CLIENT, bucket_name)

        # List the objects stored in your Cloud Storage buckets, which are ordered in the list lexicographically by name
        # https://cloud.google.com/storage/docs/listing-objects
        # No need to sort filename
        blob_list = list(settings.CLOUD_STORAGE_CLIENT.list_blobs(bucket, prefix=month))
        blob_name_list = [blob.name for blob in blob_list]
        try:
            starting_index = blob_name_list.index(starting_blobname)
            blob_list = blob_list[starting_index:]
            self.stdout.write(f"Starting with blob file named {blob_list[0]}")
        except ValueError:
            pass

        for blob in blob_list:
            file_name = blob.name
            if blob.size == 0:
                self.stdout.write(f"Skipping blob named {file_name}. Blob size is zero.")
                continue
            with blob.open(mode="r") as f:
                line_count = 0
                for line in f:
                    bq_call = json.loads(line)
                    line_count += 1
                    self.stdout.write(f"Getting or creating call with bq_call['call_id']='{bq_call['call_id']}'")
                    self.stdout.write(f"Progress made so far: file_name='{file_name}', line number {line_count} of unknown amount of lines.'")

                    self.load_call_and_analytics_dict(bq_call, options)

    def load_call_and_analytics_dict(self, bq_call: Dict, options: Dict) -> None:
        call_id = bq_call.pop("call_id")

        practice_override_id = options.get("practice_id")
        if not practice_override_id:
            practice_id = bq_call.pop("practice_id")
        else:
            practice_id = practice_override_id
            del bq_call["practice_id"]

        practice = self._get_practice_from_practice_id(practice_id)

        defaults = {}
        defaults.update(
            {
                "id": call_id,
                "call_start_time": bq_call.pop("call_start"),
                "call_end_time": bq_call.pop("call_end"),
                "practice": practice,
                "checked_voicemail": bool(bq_call.pop("checked_voicemail")),
                "went_to_voicemail": bool(bq_call.pop("went_to_voicemail")),
                "referral_source": self._get_referral_source(bq_call.pop("referral_source")),
            }
        )

        call_sentiment = bq_call.pop("call_sentiment")
        call_agent_interactions = bq_call.pop("call_agent_interaction")

        # Mentioned
        call_company_mentioned = bq_call.pop("call_company_discussed")
        call_insurance_mentioned = bq_call.pop("call_insurance_discussed")
        call_procedure_mentioned = bq_call.pop("call_procedure_discussed")
        call_product_mentioned = bq_call.pop("call_product_discussed")
        call_symptom_mentioned = bq_call.pop("call_symptom_discussed")

        call_purpose = bq_call.pop("call_purpose")
        non_agent_engagement_persona_info = bq_call.pop("non_agent_engagement_persona_info")

        # Not necessary
        del bq_call["caller_type_info"]  # TODO: remove from schema, deprecated
        del bq_call["call_pause"]  # TODO: Implement when we're determining longest pause again
        del bq_call["call_transcription"]
        del bq_call["call_transcription_fragment"]
        del bq_call["insert_timestamp"]
        del bq_call["domain"]  # TODO: remove from all extracts
        # del bq_call["site_id"]

        defaults.update(bq_call)

        peerlogic_api_call, created = Call.objects.update_or_create(pk=call_id, defaults=defaults)
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created call with pk='{peerlogic_api_call.pk}'"))

        self.stdout.write(self.style.SUCCESS(f"Updated and working with Peerlogic Call {peerlogic_api_call.pk}"))

        # self._load_agent_call_scores are garbage - removed
        self._load_call_sentiment(call_sentiment, peerlogic_api_call)
        self._load_call_purposes_and_outcomes_with_outcome_reasons(call_purpose, peerlogic_api_call)
        self._load_non_agent_engagement_persona_info(non_agent_engagement_persona_info, peerlogic_api_call)

        # Mentioned
        self._load_company_mentioned(call_company_mentioned, peerlogic_api_call)
        self._load_insurance_mentioned(call_insurance_mentioned, peerlogic_api_call)
        self._load_procedure_mentioned(call_procedure_mentioned, peerlogic_api_call)
        self._load_product_mentioned(call_product_mentioned, peerlogic_api_call)
        self._load_symptom_mentioned(call_symptom_mentioned, peerlogic_api_call)

    def _get_practice_from_practice_id(self, practice_id: str) -> Practice:
        self.stdout.write(f"Going to database to obtain practice object for practice_id='{practice_id}")
        try:
            practice = Practice.objects.get(pk=practice_id)
        except Practice.DoesNotExist:
            self.stderr.write(f"Practice practice_id='{practice_id}' does not exist! Exiting.")
            exit(2)

        return practice

    def _dedupe_non_agent_engagement_persona_info(self, call: Call) -> int:
        """
        This will go away, this is just for fixing duplicate non_agent_engagement_persona_types that
        were added in the past.

        See _load_non_agent_engagement_persona_info for examples of non_agent_engagement_persona_types.
        """
        # TODO: rename this engaged_in_calls relative name to something that makes more sense

        # Taking the last agent_engaged_with
        last_agent_engaged_with = call.engaged_in_calls.order_by("-modified_at").first()

        for agent_engaged_with in call.engaged_in_calls.exclude(pk=last_agent_engaged_with.pk).order_by("-modified_at").iterator():
            agent_engaged_with.delete()

        return len(call.engaged_in_calls.order_by("-modified_at"))

    def _load_agent_call_scores(self, call_agent_interactions, call: Call):

        for interaction in call_agent_interactions:
            metric = interaction["agent_interaction_metric_name"]
            defaults = {"raw_model_run_id": interaction["agent_interaction_metric_run_id"], "score": interaction["agent_interaction_metric_score"]}

            self.stdout.write(f"Getting or creating Agent Call Score with metric='{metric}'.")
            peerlogic_api_agent_call_score, created = AgentCallScore.objects.get_or_create(call=call, metric=metric, defaults=defaults)

            if created:
                self.stdout.write(self.style.SUCCESS(f"Created agent call score with pk='{peerlogic_api_agent_call_score.pk}'"))
            else:
                self.stdout.write(f"Not creating - Found existing agent call score with pk={peerlogic_api_agent_call_score.pk}")

    def _load_call_sentiment(self, call_sentiment, call: Call):
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

    def _load_company_mentioned(self, call_company_mentioned: Dict, call: Call) -> None:

        for company in call_company_mentioned:
            keyword = company.get("call_company_keyword")
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

    def _load_insurance_mentioned(self, call_insurance_mentioned: Dict, call: Call) -> None:

        for insurance in call_insurance_mentioned:
            keyword = insurance.get("call_insurance_keyword")
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

    def _load_procedure_mentioned(self, call_procedure_mentioned: Dict, call: Call) -> None:

        for procedure in call_procedure_mentioned:
            keyword = procedure.get("call_procedure_keyword")
            if not keyword:
                continue

            self.stdout.write(f"Updating or creating Call Mentioned Procedure with keyword='{keyword}'.")
            created = None
            try:
                peerlogic_api_call_mentioned_procedure, created = CallMentionedProcedure.objects.update_or_create(call=call, keyword=keyword)
            except CallMentionedProcedure.MultipleObjectsReturned as mor:
                self.stdout.write(f"Multiple call mentioned procedures returned with keyword='{keyword}'")
                print(mor)  # can't use self.stdout.write with an exception message
                self.stdout.write("Deduplicating call mentioned procedures.")
                call_mentioned_procedures_final_count = self._dedupe_procedure_mentioned(call)
                self.stdout.write(f"Final number of call mentioned procedures: '{call_mentioned_procedures_final_count}'")

            if created:
                self.stdout.write(self.style.SUCCESS(f"Created call mentioned procedure with pk='{peerlogic_api_call_mentioned_procedure.pk}'"))
            else:
                self.stdout.write(f"Not creating - Found existing call mentioned procedure with pk={peerlogic_api_call_mentioned_procedure.pk}")

    def _dedupe_procedure_mentioned(self, call: Call) -> int:
        """
        This will go away, this is just for fixing duplicate call_procedure_mentioned that
        were added in the past.
        """

        unique_procedure_keyword_mentioneds = set()
        for mentioned_procedure in call.mentioned_procedures.order_by("-modified_at").iterator():
            keyword = mentioned_procedure.keyword
            if keyword and keyword not in unique_procedure_keyword_mentioneds:
                unique_procedure_keyword_mentioneds.add(keyword)
            else:
                mentioned_procedure.delete()

        return len(call.mentioned_procedures.order_by("-modified_at"))

    def _load_symptom_mentioned(self, call_symptom_mentioned: Dict, call: Call) -> None:

        for symptom in call_symptom_mentioned:
            keyword = symptom.get("call_symptom_keyword")
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

    def _load_product_mentioned(self, call_product_mentioned: Dict, call: Call) -> None:

        for product in call_product_mentioned:
            keyword = product.get("call_product_keyword")
            if not keyword:
                continue

            self.stdout.write(f"Getting or creating Call Mentioned Product with keyword='{keyword}'.")
            peerlogic_api_call_mentioned_product, created = CallMentionedProduct.objects.get_or_create(
                pk=product["call_product_discussed_id"], call=call, keyword=keyword
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created call mentioned product with pk='{peerlogic_api_call_mentioned_product.pk}'"))
            else:
                self.stdout.write(f"Found call mentioned product with pk={peerlogic_api_call_mentioned_product.pk}")

    def _load_call_purposes_and_outcomes_with_outcome_reasons(self, call_purposes: Dict, call: Call) -> None:

        for bq_call_purpose in call_purposes:
            peerlogic_api_call_purpose = self._load_call_purpose(bq_call_purpose, call)
            peerlogic_api_call_outcome = self._load_call_outcome(bq_call_purpose, peerlogic_api_call_purpose)
            self._load_call_outcome_reason(bq_call_purpose, peerlogic_api_call_outcome)

    def _load_call_purpose(self, call_purpose: Dict, call: Call) -> CallPurpose:
        call_purpose_type = call_purpose["purpose"]
        if not call_purpose_type:
            return

        defaults = {"raw_call_purpose_model_run_id": call_purpose["purpose_run_id"]}

        self.stdout.write(f"Getting or creating Call Purpose with call_purpose_type='{call_purpose_type}'.")
        peerlogic_api_call_purpose, created = CallPurpose.objects.get_or_create(
            pk=call_purpose["call_purpose_id"], call=call, call_purpose_type=call_purpose_type, defaults=defaults
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created call purpose with pk='{peerlogic_api_call_purpose.pk}'"))
        else:
            self.stdout.write(f"Found call purpose with pk={peerlogic_api_call_purpose.pk}")

        return peerlogic_api_call_purpose

    def _load_call_outcome(self, call_purpose: Dict, peerlogic_api_call_purpose: CallPurpose) -> CallOutcome:
        call_outcome_type = call_purpose["outcome"]
        if not call_outcome_type:
            call_outcome_type = CallOutcomeTypes.NOT_APPLICABLE  # mark as processed

        defaults = {
            # keep the model run id the same as the purpose run id because they come from
            # the same model.
            "raw_call_outcome_model_run_id": call_purpose["purpose_run_id"]
        }

        self.stdout.write(f"Getting or creating Call Outcome with call_outcome_type='{call_outcome_type}'.")
        peerlogic_api_call_outcome, created = CallOutcome.objects.get_or_create(
            call_purpose=peerlogic_api_call_purpose, call_outcome_type=call_outcome_type, defaults=defaults
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created call outcome with pk='{peerlogic_api_call_outcome.pk}'"))
        else:
            self.stdout.write(f"Not creating - Found existing call outcome with pk={peerlogic_api_call_outcome.pk}")

        return peerlogic_api_call_outcome

    def _load_call_outcome_reason(self, call_purpose: Dict, peerlogic_api_call_outcome: CallOutcome) -> CallOutcomeReason:

        BQ_TO_PEERLOGIC_API_OUTCOME_REASON_TYPE_MAP = {
            "n/a": CallOutcomeReasonTypes.NOT_APPLICABLE,
            "not_enough_information_possesed_by_patient_or_agent": CallOutcomeReasonTypes.NOT_ENOUGH_INFORMATION_POSSESED_BY_PATIENT_OR_AGENT,
            "procedure_not_offered": CallOutcomeReasonTypes.PROCEDURE_NOT_OFFERED,
            "others": CallOutcomeReasonTypes.OTHERS,
            "day_or_time_not_available": CallOutcomeReasonTypes.DAY_OR_TIME_NOT_AVAILABLE,
            "call_interrupted": CallOutcomeReasonTypes.CALL_INTERRUPTED,
            "caller_indifference": CallOutcomeReasonTypes.CALLER_INDIFFERENCE,
            "lost": CallOutcomeReasonTypes.LOST,
            "pricing": CallOutcomeReasonTypes.PRICING,
            "treatment_not_offered": CallOutcomeReasonTypes.TREATMENT_NOT_OFFERED,
            "other": CallOutcomeReasonTypes.OTHERS,
            "scheduling": CallOutcomeReasonTypes.SCHEDULING,
            "insurance": CallOutcomeReasonTypes.INSURANCE,
            "too_expensive": CallOutcomeReasonTypes.TOO_EXPENSIVE,
            "insurance_not_taken": CallOutcomeReasonTypes.INSURANCE_NOT_TAKEN,
        }
        call_outcome_reason_type = BQ_TO_PEERLOGIC_API_OUTCOME_REASON_TYPE_MAP.get(call_purpose.get("outcome_reason"))
        if not call_outcome_reason_type:
            call_outcome_reason_type = CallOutcomeReasonTypes.NOT_APPLICABLE  # mark as processed

        defaults = {
            # keep the model run id the same as the purpose run id because they come from
            # the same model.
            "raw_call_outcome_reason_model_run_id": call_purpose["purpose_run_id"]
        }

        self.stdout.write(f"Getting or creating Call Outcome Reason with call_outcome_reason_type='{call_outcome_reason_type}'.")
        peerlogic_api_call_outcome_reason, created = CallOutcomeReason.objects.get_or_create(
            call_outcome=peerlogic_api_call_outcome, call_outcome_reason_type=call_outcome_reason_type, defaults=defaults
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created call outcome reason with pk='{peerlogic_api_call_outcome_reason.pk}'"))
        else:
            self.stdout.write(f"Not creating - Found existing call outcome reason with pk={peerlogic_api_call_outcome_reason.pk}")

        return peerlogic_api_call_outcome_reason

    def _load_non_agent_engagement_persona_info(self, non_agent_engagement_persona_info: Dict, call: Call) -> None:

        BQ_TO_PEERLOGIC_API_NON_AGENT_ENGAGEMENT_TYPE_MAP = {
            "NewPatient": NonAgentEngagementPersonaTypes.NEW_PATIENT,
            "ExistingPatient": NonAgentEngagementPersonaTypes.EXISTING_PATIENT,
            "ContractorVendor": NonAgentEngagementPersonaTypes.CONTRACTOR_VENDOR,
            "Others": NonAgentEngagementPersonaTypes.OTHERS,
            "IntraOffice": None,
        }

        non_agent_engagement_persona_type = BQ_TO_PEERLOGIC_API_NON_AGENT_ENGAGEMENT_TYPE_MAP.get(
            non_agent_engagement_persona_info.get("non_agent_engagement_persona_type")
        )
        if not non_agent_engagement_persona_type:
            return

        defaults = {"raw_non_agent_engagement_persona_model_run_id": non_agent_engagement_persona_info["non_agent_engagement_persona_run_id"]}

        self.stdout.write(f"Updating or creating Agent Engaged With with non_agent_engagement_persona_type='{non_agent_engagement_persona_type}'.")
        created = None
        try:
            peerlogic_api_agent_engaged_with, created = AgentEngagedWith.objects.update_or_create(
                call=call,
                non_agent_engagement_persona_type=non_agent_engagement_persona_type,
                defaults=defaults,
            )
        except AgentEngagedWith.MultipleObjectsReturned as mor:
            self.stdout.write(f"Multiple agent engaged withs returned with non_agent_engagement_persona_type='{non_agent_engagement_persona_type}'")
            print(mor)  # can't use self.stdout.write with an exception message
            self.stdout.write("Deduplicating agent engaged withs.")
            self._dedupe_non_agent_engagement_persona_info(call)

        if created:
            self.stdout.write(self.style.SUCCESS(f"Created agent engaged with, with pk='{peerlogic_api_agent_engaged_with.pk}'"))
        else:
            self.stdout.write(f"Not creating - Found existing agent engaged with, with pk={peerlogic_api_agent_engaged_with.pk}")

        return peerlogic_api_agent_engaged_with

    def _get_referral_source(self, bq_referral_source) -> str:
        BQ_TO_PEERLOGIC_API_REFERRAL_SOURCE_TYPE_MAP = {
            "patient_referral": ReferralSourceTypes.PATIENT_REFERRAL,
            "medical_provider": ReferralSourceTypes.MEDICAL_PROVIDER,
            "dental_provider": ReferralSourceTypes.DENTAL_PROVIDER,
            "web_search": ReferralSourceTypes.WEB_SEARCH,
            "social_media": ReferralSourceTypes.SOCIAL_MEDIA,
            "insurance": ReferralSourceTypes.INSURANCE,
            "paid_advertising": ReferralSourceTypes.PAID_ADVERTISING,
            "others": ReferralSourceTypes.OTHERS,
            "unknown": ReferralSourceTypes.OTHERS,
            "n/a": ReferralSourceTypes.NOT_APPLICABLE,
        }
        referral_source_type = BQ_TO_PEERLOGIC_API_REFERRAL_SOURCE_TYPE_MAP.get(bq_referral_source.get("referral_source_type"))
        if not referral_source_type:
            referral_source_type = ReferralSourceTypes.NOT_APPLICABLE
        return referral_source_type
