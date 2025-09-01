from django.urls import reverse
import pytz
from django.utils import timezone

class TimezoneMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tzname = request.COOKIES.get('timezone')
        if tzname:
            try:
                timezone.activate(pytz.timezone(tzname))
            except pytz.UnknownTimeZoneError:
                # If the timezone from the cookie is invalid, deactivate to use the default.
                timezone.deactivate()
        else:
            # If no timezone cookie is set, use the default.
            timezone.deactivate()
        return self.get_response(request)

class ClearSocialSessionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        """
        Clears lingering allauth social login data from the session if the user
        is accessing the admin panel. This prevents a bug where an admin trying
        to log in would be redirected to a pending social signup flow.
        """
        # Use a hardcoded path for robustness. The reverse() call can be problematic
        # during application startup or under certain server configurations.
        # The admin path is stable and unlikely to change.
        if request.path.startswith('/admin/'):
            if 'socialaccount_state' in request.session:
                del request.session['socialaccount_state']
            if 'sociallogin' in request.session:
                del request.session['sociallogin']
        
        response = self.get_response(request)
        return response
