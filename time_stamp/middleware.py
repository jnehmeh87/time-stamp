from django.utils import timezone
import pytz

class TimezoneMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tzname = request.COOKIES.get('timezone')
        if tzname:
            try:
                timezone.activate(pytz.timezone(tzname))
            except pytz.UnknownTimeZoneError:
                # If the timezone from the cookie is invalid, fall back to the default.
                timezone.deactivate()
        else:
            timezone.deactivate()
        return self.get_response(request)
