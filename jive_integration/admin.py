from django.contrib import admin

from jive_integration.models import JiveConnection, JiveChannel, JiveSession, JiveLine

admin.site.register(JiveConnection)
admin.site.register(JiveChannel)
admin.site.register(JiveSession)
admin.site.register(JiveLine)
