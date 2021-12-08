from django.contrib import admin
from django.contrib.auth.models import Group


from .forms import PracticeAdminForm
from .models import Client, User, Practice


admin.site.unregister(Group)


class ClientAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "practice",
        "rest_base_url",
    )


class PracticeAdmin(admin.ModelAdmin):
    # Use our custom form.
    form = PracticeAdminForm
    # Filter permissions horizontal as well.
    filter_horizontal = ["permissions"]


admin.site.register(User)
admin.site.register(Client, ClientAdmin)
admin.site.register(Practice, PracticeAdmin)
