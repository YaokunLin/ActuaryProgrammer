from django.contrib import admin

from .models import (
    CallMentionedCompany,
    CallMentionedInsurance,
    CallMentionedProcedure,
    CallMentionedProduct,
    CallMentionedSymptom,
    CallOutcome,
    CallOutcomeReason,
    CallPurpose,
)

class GenericMentionedAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "call",
        "keyword",
    )

class CallOutcomeAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "call",
        "call_outcome_type",
        "call_purpose",
    )

class CallPurposeAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "call",
        "call_purpose_type",
        "outcome_results",
    )

admin.site.register(CallMentionedCompany, GenericMentionedAdmin)
admin.site.register(CallMentionedInsurance, GenericMentionedAdmin)
admin.site.register(CallMentionedProcedure, GenericMentionedAdmin)
admin.site.register(CallMentionedProduct, GenericMentionedAdmin)
admin.site.register(CallMentionedSymptom, GenericMentionedAdmin)
admin.site.register(CallOutcome)
admin.site.register(CallOutcomeReason)
admin.site.register(CallPurpose, CallPurposeAdmin)
