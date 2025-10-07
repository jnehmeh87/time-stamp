from django import forms
from workspaces.models import Project
from django.core.exceptions import ValidationError
from datetime import date, timedelta
from django.contrib.auth import get_user_model

User = get_user_model()

class TimeEntryFilterForm(forms.Form):
    start_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    end_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    show_archived = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))