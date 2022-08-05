from django.contrib import admin

from .models import (
    CallLongestPause,
    CallSentiment,
    CallTranscriptFragment,
    CallTranscriptFragmentSentiment,
)

admin.site.register(CallLongestPause)
admin.site.register(CallSentiment)
admin.site.register(CallTranscriptFragment)
admin.site.register(CallTranscriptFragmentSentiment)
