from django import forms
from workspaces.models import CATEGORY_CHOICES
from django.core.exceptions import ValidationError
from datetime import date, timedelta
from allauth.account.forms import SignupForm
from django_countries.fields import CountryField
from django.contrib.auth import get_user_model

User = get_user_model()

class MultiImageInput(forms.ClearableFileInput):
    allow_multiple_selected = True
