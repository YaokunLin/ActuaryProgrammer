from django.db import models
from django.utils.translation import gettext_lazy as _


class EngagementPersonaTypes(models.TextChoices):
    AGENT = "agent"
    NON_AGENT = "non_agent"


class NonAgentEngagementPersonaTypes(models.TextChoices):
    NEW_PATIENT = "new_patient"
    EXISTING_PATIENT = "existing_patient"
    CONTRACTOR_VENDOR = "contractor_vendor"
    INSURANCE_PROVIDER = "insurance_provider"
    OTHERS = "others"


class CallConnectionTypes(models.TextChoices):
    MISSED = "missed"
    CONNECTED = "connected"


class TelecomPersonaTypes(models.TextChoices):
    CALLER = "caller"
    CALLEE = "callee"


class ReferralSourceTypes(models.TextChoices):
    PATIENT_REFERRAL = "patient_referral"
    MEDICAL_PROVIDER = "medical_provider"
    DENTAL_PROVIDER = "dental_provider"
    WEB_SEARCH = "web_search"
    SOCIAL_MEDIA = "social_media"
    INSURANCE = "insurance"
    PAID_ADVERTISING = "paid_advertising"
    NOT_APPLICABLE = "not_applicable"
    OTHERS = "others"


class CallDirectionTypes(models.TextChoices):
    INBOUND = "inbound"
    OUTBOUND = "outbound"
    INTERNAL = "internal"


class TelecomCallerNameInfoTypes(models.TextChoices):
    BUSINESS = "business"
    CONSUMER = "consumer"
    UNDETERMINED = "undetermined"  # encountered but the type is unknown


class TelecomCallerNameInfoSourceTypes(models.TextChoices):
    PEERLOGIC = "peerlogic"
    TWILIO = "twilio"


class TelecomCarrierTypes(models.TextChoices):
    LANDLINE = "landline"  # aka "fixed" or "wireline" - designation provided by the carrier
    MOBILE = "mobile"  # aka "non-fixed" or "wireless" - designation provided by the carrier
    VOIP = "voip"  # - classification on the carrier


class AudioCodecType(models.TextChoices):
    # https://developer.mozilla.org/en-US/docs/Web/Media/Formats/Audio_codecs
    AAC = "aac", _("Advanced Audio Coding")
    ALAC = "alac", _("Apple Lossless Audio Codec")
    AMR = "amr", _("Adaptive Multi-Rate")
    FLAC = "flac", _("Free Lossless Audio Codec")
    G711 = "g711", _("PCMU, G711u or G711MU for G711 μ-law, and PCMA or G711A for G711 A-law")  # https://en.wikipedia.org/wiki/G.711
    G722 = "g722", _("7 kHz Audio Coding Within 64 kbps (for telephony/VoIP)")
    MP3 = "mp3", _("MPEG-1 Audio Layer III")
    OPUS = "opus", _("Opus")
    VORBIS = "vorbis", _("MPEG-1 Audio Layer III")


class CallAudioStatusTypes(models.TextChoices):
    RETRIEVAL_FROM_PROVIDER_IN_PROGRESS = "retrieval_from_provider_in_progress"
    UPLOADING = "uploading"
    UPLOADED = "uploaded"


class SupportedAudioMimeTypes(models.TextChoices):
    # https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/MIME_types/Common_types
    # https://www.iana.org/assignments/media-types/media-types.xhtml#audio
    AUDIO_PCMU = "audio/PCMU"  # PCM MU-LAW (mlaw)
    AUDIO_GSM = "audio/GSM"  # Microsoft GSM Audio (agsm)
    AUDIO_WAV = "audio/WAV"