from django.contrib import admin

from netsapiens_integration.models import (
    NetsapiensAPICredentials,
    NetsapiensCallSubscription,
    NetsapiensCallSubscriptionEventExtract,
)

admin.site.register(NetsapiensAPICredentials)
admin.site.register(NetsapiensCallSubscription)
admin.site.register(NetsapiensCallSubscriptionEventExtract)
