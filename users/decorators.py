from functools import wraps
from django.core.exceptions import PermissionDenied

def role_required(allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                raise PermissionDenied

            organization = request.user.organizations.first()
            if not organization:
                raise PermissionDenied

            membership = organization.membership_set.get(user=request.user)
            if membership.role not in allowed_roles:
                raise PermissionDenied

            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
