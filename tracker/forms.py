from django import forms
from .models import TimeEntry, Project

class TimeEntryUpdateForm(forms.ModelForm):
    class Meta:
        model = TimeEntry
        fields = ['title', 'project', 'description', 'notes', 'category']
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
            # Populate project choices with projects owned by the current user
            self.fields['project'].queryset = Project.objects.filter(user=user)
            self.fields['project'].empty_label = "No Project"
