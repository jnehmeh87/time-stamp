from django import forms
from .models import TimeEntry, Project, TimeEntryImage, CATEGORY_CHOICES
from django.core.exceptions import ValidationError
from datetime import date

class MultiImageInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class TimeEntryUpdateForm(forms.ModelForm):
    images = forms.ImageField(
        required=False,
        widget=MultiImageInput(attrs={'class': 'form-control', 'multiple': True}),
        help_text="You can select multiple images."
    )

    class Meta:
        model = TimeEntry
        fields = ['title', 'project', 'description', 'notes', 'category', 'images']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'project': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'category': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['project'].queryset = Project.objects.filter(user=user)
            self.fields['project'].empty_label = "No Project"

    def save(self, commit=True):
        instance = super().save(commit=commit)
        image_files = self.files.getlist('images')
        if commit and image_files:
            TimeEntryImage.objects.bulk_create([
                TimeEntryImage(time_entry=instance, image=img) for img in image_files
            ])
        return instance

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
    category = forms.ChoiceField(choices=[('', 'All'), ('work', 'Work'), ('personal', 'Personal')], required=False, widget=forms.Select(attrs={'class': 'form-select'}))
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

class TimeEntryFilterForm(forms.Form):
    start_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    end_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    category = forms.ChoiceField(choices=[('', 'All'), ('work', 'Work'), ('personal', 'Personal')], required=False, widget=forms.Select(attrs={'class': 'form-select'}))
    show_archived = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
