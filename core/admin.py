from django.contrib import admin
from django.contrib.auth.models import Group


from .forms import GroupAdminForm
from .models import Client, User


admin.site.unregister(Group)


class ClientAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "group",
        "rest_base_url",
    )


class GroupAdmin(admin.ModelAdmin):
    # Use our custom form.
    form = GroupAdminForm
    # Filter permissions horizontal as well.
    filter_horizontal = ["permissions"]


admin.site.register(User)
admin.site.register(Client, ClientAdmin)
admin.site.register(Group, GroupAdmin)
