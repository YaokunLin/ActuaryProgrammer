from typing import Tuple

from django.db.models import Q

from calls.analytics.intents.field_choices import CallOutcomeTypes, CallPurposeTypes
from calls.analytics.participants.field_choices import NonAgentEngagementPersonaTypes
from calls.field_choices import CallConnectionTypes, CallDirectionTypes
from core.models import InsuranceProviderPhoneNumber, Practice

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

# Outcome
FAILURE_FILTER = Q(call_purposes__outcome_results__call_outcome_type=CallOutcomeTypes.FAILURE)
SUCCESS_FILTER = Q(call_purposes__outcome_results__call_outcome_type=CallOutcomeTypes.SUCCESS)

# Purpose
NEW_APPOINTMENT_FILTER = Q(call_purposes__call_purpose_type=CallPurposeTypes.NEW_APPOINTMENT) & (SUCCESS_FILTER | FAILURE_FILTER)

# Non-agent Engagement Persona Type
EXISTING_PATIENT_FILTER = Q(engaged_in_calls__non_agent_engagement_persona_type=NonAgentEngagementPersonaTypes.EXISTING_PATIENT)
NEW_PATIENT_FILTER = Q(engaged_in_calls__non_agent_engagement_persona_type=NonAgentEngagementPersonaTypes.NEW_PATIENT)

# Compound
NAEPT_PATIENT_FILTER = EXISTING_PATIENT_FILTER | NEW_PATIENT_FILTER
OPPORTUNITIES_FILTER = NEW_APPOINTMENT_FILTER & NAEPT_PATIENT_FILTER
NEW_PATIENT_OPPORTUNITIES_FILTER = NEW_APPOINTMENT_FILTER & NEW_PATIENT_FILTER
INBOUND_WINBACK_OPPORTUNITY_FILTER = INBOUND_FILTER & NEW_PATIENT_OPPORTUNITIES_FILTER & FAILURE_FILTER


# Industry Averages
INDUSTRY_AVERAGES_PRACTICE_CALLS_FILTER = Q(practice__include_in_benchmarks=True)
INDUSTRY_AVERAGES_PRACTICE_FILTER = Q(include_in_benchmarks=True)


# Insurance Providers
def get_insurance_provider_callee_number_filter():
    """
    This filter is created on-demand since creating it involves a DB query
    """
    return Q(sip_callee_number__in=InsuranceProviderPhoneNumber.objects.only("phone_number"))


def get_organization_filter_and_practice_count_for_practice(practice: Practice) -> Tuple[Q, int]:
    organization_filter = Q()
    num_practices = None

    organization_id = practice.organization_id
    if organization_id:
        num_practices = Practice.objects.filter(organization_id=practice.organization_id).count()
        organization_filter = Q(practice__organization_id=organization_id)

    return organization_filter, num_practices
