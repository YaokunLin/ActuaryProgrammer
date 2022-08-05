from django.contrib import admin

from .models import (
    AgentCallScore,
    AgentCallScoreMetric,
)

admin.site.register(AgentCallScore)
admin.site.register(AgentCallScoreMetric)
