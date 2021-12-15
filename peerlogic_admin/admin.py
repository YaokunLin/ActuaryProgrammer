from django.contrib.admin.sites import AdminSite


peerlogic_super_admin_site = AdminSite(name="peerlogic_super_admin_site")

peerlogic_super_admin_site.login_template = "login.html"
