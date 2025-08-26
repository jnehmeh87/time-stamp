from django import forms
from .models import TimeEntry, Project, TimeEntryImage, CATEGORY_CHOICES
from django.core.exceptions import ValidationError
from datetime import date, timedelta
from allauth.account.forms import SignupForm
from django_countries.fields import CountryField

class MultiImageInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class TimeEntryUpdateForm(forms.ModelForm):
    images = forms.FileField(
        widget=MultiImageInput(attrs={'class': 'form-control'}), 
        required=False, 
        label="Upload New Images"
    )
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
            self.fields['project'].empty_label = "No Project"

        # Populate pause fields from the model's paused_duration
        if self.instance and self.instance.paused_duration:
            seconds = self.instance.paused_duration.total_seconds()
            self.fields['pause_hours'].initial = int(seconds // 3600)
            self.fields['pause_minutes'].initial = int((seconds % 3600) // 60)
            self.fields['pause_seconds'].initial = int(seconds % 60)

    def clean(self):
        cleaned_data = super().clean()
        hours = cleaned_data.get('pause_hours') or 0
        minutes = cleaned_data.get('pause_minutes') or 0
        seconds = cleaned_data.get('pause_seconds') or 0
        
        # Combine into a timedelta and add to cleaned_data
        cleaned_data['paused_duration'] = timedelta(hours=hours, minutes=minutes, seconds=seconds)
        return cleaned_data

    def save(self, commit=True):
        # Set the model's paused_duration from our cleaned data
        self.instance.paused_duration = self.cleaned_data['paused_duration']
        
        # Save the TimeEntry instance first
        entry = super().save(commit=commit)

        # Now, handle the uploaded images
        if commit:
            for image_file in self.files.getlist('images'):
                TimeEntryImage.objects.create(time_entry=entry, image=image_file)
        
        return entry

class TimeEntryForm(forms.ModelForm):
    class Meta:
        model = TimeEntry
        fields = ['title', 'project', 'category', 'start_time', 'end_time', 'description', 'notes']
        widgets = {
            'start_time': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'end_time': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'project': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

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

class CustomSignupForm(SignupForm):
    first_name = forms.CharField(max_length=30, label='First Name', widget=forms.TextInput(attrs={'placeholder': 'First Name'}))
    last_name = forms.CharField(max_length=30, label='Last Name', widget=forms.TextInput(attrs={'placeholder': 'Last Name'}))
    country = CountryField(blank_label='(select country)').formfield()
    address = forms.CharField(max_length=255, label='Address', widget=forms.TextInput(attrs={'placeholder': 'Your address'}))
    phone_number = forms.CharField(max_length=20, label='Phone Number', widget=forms.TextInput(attrs={'placeholder': 'Your phone number'}))

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
