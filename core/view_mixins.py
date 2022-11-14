from django.db.models import Q


class MadeByMeViewSetMixin:
    @property
    def resource_made_by_me_filter(self):
        return Q(created_by=self.request.user)
