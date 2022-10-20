from django.contrib import admin

from .models import (
    AgentCallScore,
    AgentCallScoreMetric,
)


class AgentCallScoreAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "call",
        "metric",
        "score",
        "raw_model_run_id",
    )


admin.site.register(AgentCallScore, AgentCallScoreAdmin)
admin.site.register(AgentCallScoreMetric)
