from django.contrib import admin

from ringcentral_integration.models import (
    RingCentralAPICredentials,
    RingCentralCallLeg,
    RingCentralCallSubscription,
    RingCentralSessionEvent,
)

admin.site.register(RingCentralAPICredentials)
admin.site.register(RingCentralCallLeg)
admin.site.register(RingCentralCallSubscription)
admin.site.register(RingCentralSessionEvent)
