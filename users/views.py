from django.shortcuts import render
from allauth.account.views import LoginView as AllauthLoginView
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

# Create your views here.

class CustomLoginView(AllauthLoginView):
    """
    Custom login view to redirect staff members to the admin panel
    and regular users to the standard home page.
    """
    def get_success_url(self):
        if self.request.user.is_staff:
            return '/admin/'
        return '/'

@login_required
def session_keep_alive(request):
    """
    A simple view that is called by the frontend to keep the user's session alive.
    It just returns a success response. The real work is done by Django's
    session middleware, which will update the session's expiry on this request
    (since SESSION_SAVE_EVERY_REQUEST is True).
    """
    return JsonResponse({'success': True})