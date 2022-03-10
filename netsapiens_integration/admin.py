from django.contrib import admin

from netsapiens_integration.models import (
    NetsapiensAPICredentials,
    NetsapiensCallSubscriptions,
    NetsapiensCallSubscriptionsEventExtract,
)

admin.site.register(NetsapiensAPICredentials)
admin.site.register(NetsapiensCallSubscriptions)
admin.site.register(NetsapiensCallSubscriptionsEventExtract)
