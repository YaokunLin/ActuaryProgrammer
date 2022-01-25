from django.contrib import admin

from netsapiens_integration.models import (
    NetsapiensAPICredentials,
    NetsapiensCallsSubscriptionEventExtract,
    NetsapiensSubscriptionClient,
)

admin.site.register(NetsapiensAPICredentials)
admin.site.register(NetsapiensSubscriptionClient)
admin.site.register(NetsapiensCallsSubscriptionEventExtract)
