from functools import wraps
from django.shortcuts import redirect
from .models import Subscription

def subscription_required(plan_name):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('account_login')

            organization = request.user.organizations.first()
            if not organization:
                # Handle case where user has no organization
                return redirect('workspaces:home') 

            try:
                subscription = organization.subscription
                if not subscription.is_active or subscription.plan.name != plan_name:
                    return redirect('/upgrade/')
            except Subscription.DoesNotExist:
                return redirect('/upgrade/')

            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
