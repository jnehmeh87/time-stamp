from django import forms
from .models import TimeEntry, Project, TimeEntryImage, CATEGORY_CHOICES, Profile
from django.core.exceptions import ValidationError
from datetime import date, timedelta
from allauth.account.forms import SignupForm
from django_countries.fields import CountryField
from django.contrib.auth import get_user_model

User = get_user_model()

class MultiImageInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class TimeEntryManualForm(forms.ModelForm):
    pause_hours = forms.IntegerField(
        label="Hours", min_value=0, required=False, 
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'HH'})
    )
    pause_minutes = forms.IntegerField(
        label="Minutes", min_value=0, max_value=59, required=False, 
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'MM'})
    )
    pause_seconds = forms.IntegerField(
        label="Seconds", min_value=0, max_value=59, required=False, 
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'SS'})
    )

    class Meta:
        model = TimeEntry
        fields = [
            'title', 'category', 'project', 'start_time', 'end_time', 
            'description', 'notes'
        ]
        widgets = {
            'start_time': forms.DateTimeInput(
                attrs={'type': 'datetime-local', 'class': 'form-control'},
                format='%Y-%m-%dT%H:%M'
            ),
            'end_time': forms.DateTimeInput(
                attrs={'type': 'datetime-local', 'class': 'form-control'},
                format='%Y-%m-%dT%H:%M'
            ),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'project': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['project'].queryset = Project.objects.filter(user=user)
        else:
            # If no user is provided (e.g., in Django admin), show an empty queryset.
            self.fields['project'].queryset = Project.objects.none()
        self.fields['project'].empty_label = "No Project"

        # Populate pause fields from the model's paused_duration
        if self.instance and self.instance.paused_duration:
            seconds = self.instance.paused_duration.total_seconds()
            self.fields['pause_hours'].initial = int(seconds // 3600)
            self.fields['pause_minutes'].initial = int((seconds % 3600) // 60)
            self.fields['pause_seconds'].initial = int(seconds % 60)

    def clean(self):
        cleaned_data = super().clean()
        project = cleaned_data.get('project')

        # If a project is selected, its category should be the source of truth.
        # This ensures data consistency and centralizes the logic in the form.
        if project:
            cleaned_data['category'] = project.category

        hours = cleaned_data.get('pause_hours') or 0
        minutes = cleaned_data.get('pause_minutes') or 0
        seconds = cleaned_data.get('pause_seconds') or 0
        
        # Combine into a timedelta and add to cleaned_data
        cleaned_data['paused_duration'] = timedelta(hours=hours, minutes=minutes, seconds=seconds)

        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')

        # Add validation for time and duration logic
        if start_time and end_time:
            if start_time >= end_time:
                raise ValidationError("End time must be after start time.")
            
            duration = end_time - start_time
            if cleaned_data.get('paused_duration') > duration:
                raise ValidationError("Paused duration cannot be greater than the total entry duration.")

        return cleaned_data

    def save(self, commit=True):
        # Get the instance but don't save it to the database yet.
        instance = super().save(commit=False)
        
        # Set the paused_duration from the cleaned data, providing a default.
        instance.paused_duration = self.cleaned_data.get('paused_duration', timedelta(0))
        
        if commit:
            instance.save()
            
        return instance

class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['name', 'description', 'category', 'hourly_rate']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'hourly_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

class TimeEntryFilterForm(forms.Form):
    start_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    end_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    category = forms.ChoiceField(choices=[('', 'All Categories')] + CATEGORY_CHOICES, required=False, widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_category'}))
    show_archived = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))

class ReportForm(forms.Form):
    start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    end_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    category = forms.ChoiceField(choices=[('', 'All Categories')] + CATEGORY_CHOICES, required=False, widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_category'}))
    project = forms.ModelChoiceField(queryset=Project.objects.none(), required=False, widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_project'}))

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        projects = Project.objects.filter(user=user)
        
        # If a category is selected in the form data, filter projects by it
        if self.data.get('category'):
            projects = projects.filter(category=self.data['category'])
            
        self.fields['project'].queryset = projects

class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ('country', 'address', 'phone_number')
        widgets = {
            'country': forms.Select(attrs={'class': 'form-select'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_phone_number'}),
        }

class CustomSignupForm(SignupForm):
    first_name = forms.CharField(max_length=30, label='First Name', widget=forms.TextInput(attrs={'placeholder': 'First Name'}))
    last_name = forms.CharField(max_length=30, label='Last Name', widget=forms.TextInput(attrs={'placeholder': 'Last Name'}))
    country = CountryField(blank_label='(select country)').formfield(required=False)
    address = forms.CharField(max_length=255, label='Address', widget=forms.TextInput(attrs={'placeholder': 'Your address'}), required=False)
    phone_number = forms.CharField(max_length=20, label='Phone Number', widget=forms.TextInput(attrs={'placeholder': 'Your phone number'}), required=False)

    def save(self, request):
        user = super(CustomSignupForm, self).save(request)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.save()

        # Save profile data
        user.profile.country = self.cleaned_data['country']
        user.profile.address = self.cleaned_data['address']
        user.profile.phone_number = self.cleaned_data['phone_number']
        user.profile.save()

        return user
