import logging
from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from pydantic.dataclasses import dataclass
from shortuuid import ShortUUID


class Config:
    arbitrary_types_allowed = True


log = logging.getLogger(__name__)


# TODO: Call Partial - sip_callee_extension?

# TODO: find all keys throughout full codebase and use Call fields


class AuditModelBase(BaseModel):
    created_at: Optional[datetime]
    created_by: Optional[str]
    modified_at: Optional[datetime]
    modified_by: Optional[str]


class Call(AuditModelBase):
    id: Optional[str]  # ids do not exist when we're creating it and a persisted one hasn't been created in the database

    call_start_time: datetime
    call_end_time: datetime

    duration_seconds: Optional[str]
    connect_duration_seconds: Optional[str]
    progress_time_seconds: Optional[str]

    call_direction: Optional[str]  # optional when updating
    sip_caller_number: Optional[str]  # optional when updating
    sip_caller_name: Optional[str]  # optional when updating
    sip_callee_number: Optional[str]  # optional when updating
    sip_callee_name: Optional[str]  # optional when updating

    checked_voicemail: bool
    went_to_voicemail: bool

    call_connection: str  # connected
    who_terminated_call: str  # caller / callee

    caller_type: str  # agent / non-agent
    callee_type: str  # agent / non-agent

    practice: Optional[str]  # shortuuid, optional when updating

    referral_source: str  # does not exist in Peerlogic, exists in BigQuery


@dataclass(config=Config)
class CallAudio(object):
    id: ShortUUID
    call: ShortUUID
    mime_type: str
    status: str
    signed_url: str


class CallPurpose(AuditModelBase):
    id: Optional[str]

    call: str  # shortuuid
    call_purpose_type: str
    raw_call_purpose_model_run_id: str  # shortuuid, temporary until we create a run history table in api


class CallOutcome(AuditModelBase):
    id: Optional[str]

    call_purpose: str  # shortuuid
    call_outcome_type: str
    raw_call_outcome_model_run_id: str  # shortuuid, temporary until we create a run history table in api


class CallOutcomeReason(AuditModelBase):
    id: Optional[str]

    call_outcome: str  # shortuuid
    call_outcome_reason_type: str
    raw_call_outcome_reason_model_run_id: str  # shortuuid, temporary until we create a run history table in api


class CallTranscript(BaseModel):
    id: str

    signed_url: str  # Google signed url
    transcript_type: str

    raw_call_transcript_model_run_id: str

    text: Optional[str]  # full text


class NetsapiensAPICredentials(BaseModel):
    id: str
    created_at: datetime
    created_by: Optional[str]
    modified_at: datetime
    modified_by: Optional[str]
    voip_provider: str
    api_url: str

    client_id: str
    client_secret: str
    username: str
    password: str
    active: bool


class TelecomCallerNameInfo(AuditModelBase):
    # Expected format as of 2021-12-10
    phone_number: str  # "+12345678900",
    caller_name: str  # "CNAME or blank",
    caller_name_type: str  # "undetermined or consumer or business",
    source: str  # "twilio or peerlogic",
    carrier_name: str  # "Vonage/Nexmo - Sybase365",
    carrier_type: str  # "voip or landline or mobile",
    mobile_country_code: Optional[str]  # 311,
    mobile_network_code: Optional[str]  # 900,

    def is_business(self) -> bool:
        business_types = ("business",)
        return self.caller_name_type in business_types

    def is_consumer_carrier_type(self) -> bool:
        consumer_carrier_types = ("mobile",)
        return self.carrier_type in consumer_carrier_types


class AgentEngagedWith(AuditModelBase):
    id: Optional[str]
    call: str
    non_agent_engagement_persona_type: str
    raw_non_agent_engagement_persona_model_run_id: str
