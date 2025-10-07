from django import forms
from .models import TimeEntry, Project, Contact
from django.core.exceptions import ValidationError
from datetime import timedelta
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
            'title', 'project', 'start_time', 'end_time', 
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
            'project': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            # Filter projects by organizations the user is a member of
            self.fields['project'].queryset = Project.objects.filter(organization__members=user)
        else:
            self.fields['project'].queryset = Project.objects.none()
        self.fields['project'].empty_label = "No Project"

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
        
        cleaned_data['paused_duration'] = timedelta(hours=hours, minutes=minutes, seconds=seconds)

        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')

        if start_time and end_time:
            if start_time >= end_time:
                raise ValidationError("End time must be after start time.")
            
            duration = end_time - start_time
            if cleaned_data.get('paused_duration') > duration:
                raise ValidationError("Paused duration cannot be greater than the total entry duration.")

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.paused_duration = self.cleaned_data.get('paused_duration', timedelta(0))
        if commit:
            instance.save()
        return instance

class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['name', 'description', 'hourly_rate']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'hourly_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

class ClientForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = ['name', 'email', 'billing_address', 'vat_id', 'send_reminders']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'billing_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'vat_id': forms.TextInput(attrs={'class': 'form-control'}),
            'send_reminders': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
        }