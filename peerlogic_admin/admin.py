from django.contrib.admin.sites import AdminSite


# WIP: one day we will use our own to use a token in the login / session
# it will also include all the permissions for viewing the ModelAdmin
# When I tried using this once I logged in as the superuser I could not see any models

peerlogic_super_admin_site = AdminSite(name="peerlogic_super_admin_site")

peerlogic_super_admin_site.login_template = "login.html"
