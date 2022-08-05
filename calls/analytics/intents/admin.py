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

admin.site.register(CallMentionedCompany)
admin.site.register(CallMentionedInsurance)
admin.site.register(CallMentionedProcedure)
admin.site.register(CallMentionedProduct)
admin.site.register(CallMentionedSymptom)
admin.site.register(CallOutcome)
admin.site.register(CallOutcomeReason)
admin.site.register(CallPurpose)
