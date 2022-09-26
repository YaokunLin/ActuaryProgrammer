from django.db.models import Q

from calls.analytics.intents.field_choices import CallOutcomeTypes, CallPurposeTypes
from calls.analytics.participants.field_choices import NonAgentEngagementPersonaTypes
from calls.field_choices import CallConnectionTypes, CallDirectionTypes

# Connections
CONNECTED_FILTER = Q(call_connection=CallConnectionTypes.CONNECTED)
MISSED_FILTER = Q(call_connection=CallConnectionTypes.MISSED)

# Answered / Voicemail
ANSWERED_FILTER = CONNECTED_FILTER & Q(went_to_voicemail=False)
WENT_TO_VOICEMAIL_FILTER = Q(went_to_voicemail=True)

# Direction
INBOUND_FILTER = Q(call_direction=CallDirectionTypes.INBOUND)
INTERNAL_FILTER = Q(call_direction=CallDirectionTypes.INTERNAL)
OUTBOUND_FILTER = Q(call_direction=CallDirectionTypes.OUTBOUND)

# Purpose
NEW_APPOINTMENT_FILTER = Q(call_purposes__call_purpose_type=CallPurposeTypes.NEW_APPOINTMENT)

# Outcome
FAILURE_FILTER = Q(call_purposes__outcome_results__call_outcome_type=CallOutcomeTypes.FAILURE)
SUCCESS_FILTER = Q(call_purposes__outcome_results__call_outcome_type=CallOutcomeTypes.SUCCESS)

# Non-agent Engagement Persona Type
EXISTING_PATIENT_FILTER = Q(engaged_in_calls__non_agent_engagement_persona_type=NonAgentEngagementPersonaTypes.EXISTING_PATIENT)
NEW_PATIENT_FILTER = Q(engaged_in_calls__non_agent_engagement_persona_type=NonAgentEngagementPersonaTypes.NEW_PATIENT)

# Compound
NAEPT_PATIENT_FILTER = EXISTING_PATIENT_FILTER | NEW_PATIENT_FILTER
OPPORTUNITIES_FILTER = NEW_APPOINTMENT_FILTER & NAEPT_PATIENT_FILTER

# Benchmarks
BENCHMARK_PRACTICE_CALLS_FILTER = Q(practice__include_in_benchmarks=True)
BENCHMARK_PRACTICE_FILTER = Q(include_in_benchmarks=True)
