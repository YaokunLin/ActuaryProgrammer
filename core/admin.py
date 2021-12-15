from django.contrib import admin
from django.contrib.auth.models import Group


from .models import (
    Client,
    Practice,
    User,
)


admin.site.unregister(Group)


class ClientAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "client_type",
        "practice",
        "rest_base_url",
    )


admin.site.register(User)
admin.site.register(Practice)
admin.site.register(Client, ClientAdmin)
