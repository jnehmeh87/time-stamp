from django.core.exceptions import PermissionDenied

class OrganizationPermissionMixin:
    """
    A mixin that ensures that the user is a member of the organization
    associated with the object being accessed.
    """
    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.is_authenticated:
            organization = self.request.user.organizations.first()
            if organization:
                return qs.filter(organization=organization)
        raise PermissionDenied
