from django.contrib import admin

from netsapiens_integration.models import (
    NetsapiensAPICredentials,
    NetsapiensCallsSubscription,
    NetsapiensCallsSubscriptionEventExtract,
)

admin.site.register(NetsapiensAPICredentials)
admin.site.register(NetsapiensCallsSubscription)
admin.site.register(NetsapiensCallsSubscriptionEventExtract)
