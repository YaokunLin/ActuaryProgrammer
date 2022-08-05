from django.contrib import admin

import calls.analytics.interactions.admin
from .models import (
    Call,
    CallAudio,
    CallAudioPartial,
    CallLabel,
    CallPartial,
    CallTranscript,
    CallTranscriptPartial,
    TelecomCallerNameInfo,
)

admin.site.register(Call)
admin.site.register(CallAudio)
admin.site.register(CallAudioPartial)
admin.site.register(CallLabel)
admin.site.register(CallPartial)
admin.site.register(CallTranscript)
admin.site.register(CallTranscriptPartial)
admin.site.register(TelecomCallerNameInfo)
