from django.contrib import admin

from jive_integration.models import (
    JiveAPICredentials,
    JiveChannel,
    JiveLine,
    JiveSession,
)

admin.site.register(JiveAPICredentials)
admin.site.register(JiveChannel)
admin.site.register(JiveSession)
admin.site.register(JiveLine)
