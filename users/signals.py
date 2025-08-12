from django.dispatch import receiver
from allauth.account.signals import user_signed_up
import logging

logger = logging.getLogger('users')

@receiver(user_signed_up)
def user_signed_up_receiver(request, user, sociallogin=None, **kwargs):
    updated = False
    try:
        if sociallogin:
            data = getattr(getattr(sociallogin, "account", None), "extra_data", {}) or {}
            name_field = data.get('name', '')
            if not data.get('given_name') and name_field:
                parts = name_field.split()
                if parts:
                    data.setdefault('given_name', parts[0])
                if len(parts) > 1:
                    data.setdefault('family_name', ' '.join(parts[1:]))
            first = data.get('given_name') or data.get('first_name')
            last = data.get('family_name') or data.get('last_name')
            if first:
                user.first_name = first; updated = True
            if last:
                user.last_name = last; updated = True
        else:
            form = kwargs.get('form')
            if form and getattr(form, 'cleaned_data', None):
                cd = form.cleaned_data
                for field in ['first_name', 'last_name', 'date_of_birth', 'address', 'phone_number']:
                    val = cd.get(field)
                    if val:
                        setattr(user, field, val)
                        updated = True
        if updated:
            user.save()
            logger.info("Post-signup enrichment applied for user %s", user.pk)
    except Exception as e:
        logger.warning("Post-signup enrichment failed for user %s: %s", user.pk, e)
