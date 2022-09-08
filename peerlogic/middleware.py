import backports.zoneinfo as zoneinfo
from django.utils import timezone


class TimezoneMiddleware:

    # Must be a tuple
    TZ_AWARE_PATH_PREFIXES = ("/api/calls/aggregates/",)

    # Here we define an override timezone to apply to certain paths.
    # This might differ from a timezone we might set in settings.py
    DEFAULT_TZ = "America/Creston"  # Static MST like Phoenix AZ

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        timezone_changed = False
        if request.path.startswith(self.TZ_AWARE_PATH_PREFIXES):
            header_name = "HTTP_TIMEZONE"
            tzname = request.META.get(header_name)
            if tzname and tzname in zoneinfo.available_timezones():
                timezone.activate(zoneinfo.ZoneInfo(tzname))
            else:
                timezone.activate(self.DEFAULT_TZ)

        response = self.get_response(request)
        if timezone_changed:
            timezone.deactivate()
        return response
