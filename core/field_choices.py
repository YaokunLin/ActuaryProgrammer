from django.db import models
from django.utils.translation import gettext_lazy as _


class FileStatusTypes(object):
    RETRIEVAL_FROM_PROVIDER_IN_PROGRESS = "retrieval_from_provider_in_progress"
    UPLOADING = "uploading"
    UPLOADED = "uploaded"

    class Meta:
        abstract = True


class IndustryTypes(models.TextChoices):
    DENTISTRY_GENERAL = "dentistry_general"
    DENTISTRY_PEDIATRIC = "dentistry_pediatric"
    DENTISTRY_ORTHODONTIC = "dentistry_orthodontic"
    DENTISTRY_COSMETIC = "dentistry_cosmetic"
    DENTISTRY_PERIODONTIC = "dentistry_periodontic"
    DENTISTRY_PROSTHODONTIC = "dentistry_prosthodontic"
    DENTISTRY_ENDODONTIC = "dentistry_endodontic"
    DENTISTRY_ORAL_SURGERY = "dentistry_oral_surgery"
    DENTISTRY_OTHERS = "dentistry_others"
    OTHERS = "others"


class VoipProviderIntegrationTypes(models.TextChoices):
    NETSAPIENS = "netsapiens"
    JIVE = "jive", _("GoTo / Jive")


class OAuthTokenTypes(models.TextChoices):
    ACCESS_TOKEN = "access_token"
    ID_TOKEN = "id_token"
    REFRESH_TOKEN = "refresh_token"

class OAuthCodeTypes(models.TextChoices):
    AUTHORIZATION_CODE = "authorization_code"