from django.contrib import admin

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
import calls.analytics.intents.admin  # import admin so it gets registered, DO NOT REMOVE
import calls.analytics.interactions.admin  # import admin so it gets registered, DO NOT REMOVE
import calls.analytics.participants.admin  # import admin so it gets registered, DO NOT REMOVE
import calls.analytics.transcripts.admin  # import admin so it gets registered, DO NOT REMOVE


class CallAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "call_start_time",
        "call_end_time",
        "practice",
        "call_direction",
    )


admin.site.register(Call, CallAdmin)
admin.site.register(CallAudio)
admin.site.register(CallAudioPartial)
admin.site.register(CallLabel)
admin.site.register(CallPartial)
admin.site.register(CallTranscript)
admin.site.register(CallTranscriptPartial)
admin.site.register(TelecomCallerNameInfo)
