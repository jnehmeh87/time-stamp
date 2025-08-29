from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model
import re

User = get_user_model()

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        """
        Invoked just after a user successfully authenticates via a
        social provider, but before the login is actually processed.
        This is our chance to pre-fill user data for new users.
        """
        user = sociallogin.user
        
        # If the user is new (has no primary key), generate a unique username
        if not user.pk:
            # Try to generate a base username from email
            email = sociallogin.account.extra_data.get('email')
            if email:
                # Take the part of the email before the "@"
                username_base = email.split('@')[0].lower()
                # Remove any characters that are not letters or numbers
                username_base = re.sub(r'[^a-z0-9]', '', username_base)
            else:
                # Fallback to first/last name if email is not available
                first_name = sociallogin.account.extra_data.get('given_name', '')
                last_name = sociallogin.account.extra_data.get('family_name', '')
                username_base = f"{first_name}{last_name}".lower()
                username_base = re.sub(r'[^a-z0-9]', '', username_base)

            # Ensure the username is not empty
            if not username_base:
                username_base = "user"

            # Check for uniqueness and append a number if needed
            username = username_base
            i = 1
            while User.objects.filter(username=username).exists():
                username = f"{username_base}{i}"
                i += 1
            
            user.username = username

            # Populate first and last name from social account data if they are empty
            if not user.first_name:
                user.first_name = sociallogin.account.extra_data.get('given_name', '')
            if not user.last_name:
                user.last_name = sociallogin.account.extra_data.get('family_name', '')
