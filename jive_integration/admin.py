from django.contrib import admin

from jive_integration.models import JiveAPICredentials, JiveChannel, JiveSession, JiveLine

admin.site.register(JiveAPICredentials)
admin.site.register(JiveChannel)
admin.site.register(JiveSession)
admin.site.register(JiveLine)
