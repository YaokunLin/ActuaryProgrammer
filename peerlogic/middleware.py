import backports.zoneinfo as zoneinfo
from django.utils import timezone


class TimezoneMiddleware:
    # Here we define an override timezone to apply to certain paths.
    # This might differ from a timezone we might set in settings.py
    DEFAULT_TZ = "UTC"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        header_name = "HTTP_TIMEZONE"
        tzname = request.META.get(header_name)
        if tzname and tzname in zoneinfo.available_timezones():
            timezone.activate(zoneinfo.ZoneInfo(tzname))
        else:
            timezone.activate(self.DEFAULT_TZ)

        try:
            return self.get_response(request)
        finally:
            timezone.deactivate()
