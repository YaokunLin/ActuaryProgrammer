from django.contrib import admin
from django.contrib.auth.models import Group

from core.forms import PracticeAdminForm

from .models import (
    Agent,
    Client,
    Organization,
    Patient,
    Practice,
    PracticeTelecom,
    User,
    UserPatient,
    UserTelecom,
    VoipProvider,
)

admin.site.unregister(Group)


class UserAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "username",
        "email",
        "auth0_id",
        "is_staff",
        "is_superuser",
    )


class UserTelecomAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "telecom_user",
        "username",
        "phone_sms",
        "phone_callback",
    )


class ClientAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "practice",
        "rest_base_url",
    )


class VoipProviderAdmin(admin.ModelAdmin):
    list_display = ("id", "company_name", "integration_type")


class AgentAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "practice")


class PracticeAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "active", "industry", "organization")
    form = PracticeAdminForm


class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("id", "name")


class PracticeTelecomAdmin(admin.ModelAdmin):
    list_display = ("id", "practice", "domain", "voip_provider")


class PatientAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "organization",
        "name",
    )


class UserPatientAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "patient")


admin.site.register(Agent, AgentAdmin)
admin.site.register(Client, ClientAdmin)
admin.site.register(Patient, PatientAdmin)
admin.site.register(Practice, PracticeAdmin)
admin.site.register(Organization, OrganizationAdmin)
admin.site.register(PracticeTelecom, PracticeTelecomAdmin)
admin.site.register(User, UserAdmin)
admin.site.register(UserPatient, UserPatientAdmin)
admin.site.register(UserTelecom, UserTelecomAdmin)
admin.site.register(VoipProvider, VoipProviderAdmin)
