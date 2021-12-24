from django.contrib import admin
from django.contrib.auth.models import Group

from core.forms import PracticeAdminForm

from .models import Agent, Client, Practice, User

admin.site.unregister(Group)


class UserAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "email",
        "is_staff",
        "is_superuser",
    )


class ClientAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "practice",
        "rest_base_url",
    )


class PracticeAdmin(admin.ModelAdmin):
    form = PracticeAdminForm


admin.site.register(User, UserAdmin)
admin.site.register(Agent)
admin.site.register(Practice, PracticeAdmin)
admin.site.register(Client, ClientAdmin)
