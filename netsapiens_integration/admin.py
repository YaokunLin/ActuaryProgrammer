from django.contrib import admin

from netsapiens_integration.models import (
    NetsapiensAPICredential,
    NetsapiensCallSubscription,
    NetsapiensCallSubscriptionEventExtract,
)

admin.site.register(NetsapiensAPICredential)
admin.site.register(NetsapiensCallSubscription)
admin.site.register(NetsapiensCallSubscriptionEventExtract)
